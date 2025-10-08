from threading import Thread, Event
from abc import ABC, abstractmethod

class PausableWorker(Thread, ABC):
    """
    Base class for workers that can be paused/resumed without thread 
    termination, in philosophy similar to PyQt threads.

    Subclasses must implement:
        - work(): Contains the main work loop
        - cleanup(): (Optional) Called after work() completes or on thread termination
    
    Usage:
        class MyWorker(PausableWorker):
            def work(self):
                while self._pause_event.is_set() and not self._stop_event.is_set():
                    # Do work here
                    pass
            
            def cleanup(self):
                # Optional cleanup
                pass
        
        worker = MyWorker(running=True)
        worker.start()      # Start the thread
        worker.pause()      # Pause (thread stays alive)
        worker.resume()     # Resume
        worker.stop()       # Terminate completely
    """
    def __init__(self, running: bool = False, logger=None):
        """
        Initialize the pausable worker.
        
        Args:
            running: If True, start in running state. If False, start paused.
            logger: Optional logger for debugging
        """
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
        """
        Override this method with worker logic.
        
        Example:
            while self.is_running():
                # Do work here
                pass
        """
        pass
    
    def cleanup(self):
        """
        Override this for cleanup logic when thread terminates.
        Called automatically when thread stops.
        """
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

    @property
    def is_paused(self):
        """Returns True if worker is paused (thread alive but not working)"""
        return self.is_alive() and not self._pause_event.is_set()
    
    @property
    def is_stopped(self):
        """Returns True if worker has been commanded to stop"""
        return self._stop_event.is_set()
