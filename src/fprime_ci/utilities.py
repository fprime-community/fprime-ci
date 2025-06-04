
import sys
import logging
import selectors
import threading
import time
from enum import Enum
from functools import reduce
from io import IOBase
from typing import List, Union


class Stream(Enum):
    """ Streams to handle """
    OUT = "standard out"
    ERROR = "standard error"

class IOLogger(IOBase):
    """ Convert write calls to standard logging
    
    This class can intercept `write` calls and pass the content to an assigned
    logger. It acts as a context manager so that the duration of intercept
    is limited to that scope.
    """

    def __init__(self, interceptee: Stream, severity: int, logger_name:str=None, prefix: str="", capture=False):
        """ Initialize this logger

        Initializes this logger to intercept `interceptee` and log it at the supplied `severity`. Since this is a
        context manager, actual interception must wait until the __enter__ method is called.
        
        Args:
            interceptee: stream to redirect into a log (Stream.OUT, Stream.ERROR)
            severity: severity to use when logging
            logger_name: (optional) logger name to use. Default: interceptee.value
            prefix: (optional) prefix to put before log message. Default: ""
        """
        logger_name = logger_name or interceptee.value
        self.logger = logging.getLogger(logger_name)
        self.interceptee = interceptee
        self.severity = severity
        self.buffer = ""
        self.original = None
        self.prefix = prefix
        self.data = ""
        self.capture = capture

    def write(self, data: Union[str, bytes]):
        """ Handle the incoming 'write' data
        
        Write the data to the buffer and then send out the data to the logger trigger by a newline character. This
        will support both `byte` strings and `str` strings.

        Args:
            data: str or bytes to intercept
        """
        new_data = data if isinstance(data, str) else data.decode(errors="replace")
        self.buffer += new_data
        if self.capture:
            self.data += new_data
        lines = self.buffer.split("\n")
        self.buffer = lines[-1]
        # Log out complete lines
        for line in lines[:-1]:
            self.logger.log(self.severity, f"{self.prefix}{line}")

    @staticmethod
    def communicate(file_descriptors: list, loggers: List["IOLogger"], timeout:float=10, end=None, close:int=True):
        """
        Communicates with a process while assuring that output is captured and optionally printed. This will buffer
        lines for the standard out file handle when not none, and will always buffer standard error so that it can be
        provided when needed. This effectively replaces the .communicate method of the proc itself, while still
        preventing deadlocks.  The output is returned for each stream as a list of lines.

        :param file_descriptors: list of at least one file descriptor to log
        :param loggers: list of logger objects receive file descriptor data
        :param timeout: timeout in seconds to wait for the process to finish. None to disable.
        :param end: function supplied with data to look for custom end condition
        :param close: whether to close the file handles when finished
        """
        assert len(file_descriptors) == len(loggers), "Must provide exactly 1 logger for each file descriptor"
        # Selection will allow us to read from and file descriptor whenever either is available. This will allow the
        # program to capture all data, while still printing as soon as is possible. This will keep the data logged in
        # near real time without merging streams
        #
        # Selection blocks on the read of any file descriptor, and then passes off the execution to the below code
        # with a key that represents which descriptor was the one available to read without blocking.
        selector = selectors.DefaultSelector()
        for index, (file_descriptor, logger) in enumerate(zip(file_descriptors, loggers)):
            selector.register(file_descriptor, selectors.EVENT_READ, data=(index, logger))

        start_time = time.time()
        def done(line: str, index: int):
            """ Check if the selector loop is done

            Check to see if all file descriptors are close, time out has been reached, or a custom end-condition was
            detected in the data. The custom end condition is permitted to operate on the last line of the read data and
            will be supplied an index of the file descriptor source of that line.

            Args:
                line: last line of data to check
                index: index of the file descriptor to check
            """
            custom_condition = end if end is not None else lambda line, index: False
            all_closed = reduce(lambda closed, fd: closed and fd.closed, file_descriptors, True)
            timed_out = timeout is not None and (time.time() - start_time) > timeout

            return all_closed or timed_out or custom_condition(line, index)

        try:
            index = 0
            last_line = ""
            while not done(last_line, index):
                # This line *BLOCKS* until on of the above registered handles is available to read. Then a set of events is
                # returned signaling that a given object is available for IO.
                events = selector.select(timeout=0.010) # Timeout after 10ms to keep polling done
                for key, _ in events:
                    index, io_logger = key.data
                    try:
                        read_data = key.fileobj.read(1)
                        read_data = read_data if isinstance(read_data, str) else read_data.decode(errors="replace")
                    # Some systems (like running inside Docker) raise an io error instead of returning "" when the device
                    # is ended. Not sure why this is, but the effect is the same, on IOError assume end-of-input
                    except OSError:
                        read_data = ""
                    # Streams are EOF when the line returned is empty. Once this occurs, we are responsible for closing the
                    # stream and thus closing the select loop. Empty strings need not be printed.
                    if len(read_data) >= 1:
                        last_line = io_logger.buffer + read_data
                        io_logger.write(read_data)
                    else:
                        last_line = ""
                        io_logger.write("\n")
                        if close:
                            key.fileobj.close()
        finally:
            delta_time = time.time() - start_time
            if close:
                [file_descriptor.close() for file_descriptor in file_descriptors]
        # Check for timeout condition
        if timeout is not None and delta_time > timeout:
            raise TimeoutError("Timed out waiting for i/o to finish")
        return delta_time

    @staticmethod
    def async_communicate(file_descriptors: list, loggers: List["IOLogger"], timeout=None, end=None, close: int = True):
        """ Moves data from file descriptor to loggers asynchronously.

        This function starts up a thread to wrap IOLogger.communicate. Used to perform this operation while running
        other items in the background.

        Note: IOLoggers are not thread-safe and neither are the file descriptors provided. Neither should be used until
        the associated IOLogger.join_communicate has been called.

        :param file_descriptors: list of at least one file descriptor to log
        :param loggers: list of logger objects receive file descriptor data
        :param timeout: timeout in seconds before exiting the thread
        :param end: function supplied with data to look for custom end condition
        :param close: whether to close the file handles when finished
        :return thread handle to pass to IOLogger.join_communicate
        """
        end=end if end is not None else lambda line, index: False
        stop_thread = threading.Event()

        def end_function(line, index):
            """ Responds to the custom end condition or the thread stop event """
            return end(line, index) or stop_thread.is_set()

        thread = threading.Thread(target=IOLogger.communicate,
                                  args=(file_descriptors, loggers, timeout, end_function, close))
        thread.start()
        return stop_thread, thread

    @staticmethod
    def join_communicate(thread_handle):
        """ Initiate the stop function and join to a previous async_communicate call """
        stop_thread, thread = thread_handle
        stop_thread.set()
        thread.join()

    def __enter__(self):
        """ Start the interception """
        if self.interceptee == Stream.OUT:
            self.original = sys.stdout
            sys.stdout = self
        elif self.interceptee == Stream.ERROR:
            self.original = sys.stderr
            sys.stderr = self

    def __exit__(self, type, value, traceback):
        """ Stop the interception """
        if self.interceptee == Stream.OUT:
            sys.stdout = self.original
        elif self.interceptee == Stream.ERROR:
            sys.stderr = self.original

