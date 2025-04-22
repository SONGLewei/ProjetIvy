class IvyBus:
    def __init__(self):
        self._subscribers = {}

    def subscribe(self, event_name, callback):
        if event_name not in self._subscribers:
            self._subscribers[event_name] = []
        self._subscribers[event_name].append(callback)

    def publish(self, event_name, data=None):
        if event_name in self._subscribers:
            for callback in self._subscribers[event_name]:
                callback(data)

    def unsubscribe(self, event_name, callback=None):
        """
        Unsubscribe a callback from an event.
        If callback is None, remove all callbacks for this event.
        """
        if event_name in self._subscribers:
            if callback is None:
                self._subscribers[event_name] = []
            else:
                if callback in self._subscribers[event_name]:
                    self._subscribers[event_name].remove(callback)

ivy_bus = IvyBus()
