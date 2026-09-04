from abc import ABC, abstractmethod
from threading import Event, Thread


class PausableWorker(Thread, ABC):
    """A thread that can be paused and resumed without being torn down.

    Subclasses implement ``work()`` and, optionally, ``cleanup()``.
    """

    def __init__(self, running: bool = False, logger=None):
        """``running=False`` starts the worker paused."""
        super().__init__()
        self.daemon = True
        self.logger = logger

        # Threading control
        self._pause_event = Event()
        self._stop_event = Event()

        if running:
            self._pause_event.set()

    def run(self):
        """Main thread loop - stays alive until stop() is called"""
        while not self._stop_event.is_set():
            # Wait here when paused
            self._pause_event.wait()

            # Check if we should stop
            if self._stop_event.is_set():
                break

            # Do the actual work
            self.work()

        # Cleanup when thread terminates
        self.cleanup()

    @abstractmethod
    def work(self):
        """Worker logic. Loop while ``self.is_running()``."""
        pass

    def cleanup(self):
        """Called automatically when the thread stops."""
        pass

    def pause(self):
        """Pause the worker (thread stays alive)"""
        self._pause_event.clear()

    def resume(self):
        """Resume the worker"""
        self._pause_event.set()

    def stop(self):
        """Terminate the thread completely"""
        self._stop_event.set()
        self._pause_event.set()  # Unblock if waiting

    @property
    def is_running(self):
        """Returns True if worker is actively running (not paused or stopped)"""
        return self._pause_event.is_set() and not self._stop_event.is_set()
