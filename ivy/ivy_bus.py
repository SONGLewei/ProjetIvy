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

ivy_bus = IvyBus()
