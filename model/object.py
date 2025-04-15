from abc import ABC, abstractmethod

class Object(ABC):
    def __init__(self, start, end):
        """
        Base class for all drawable objects.
        
        Parameters:
            start: (x, y) coordinate tuple representing the starting point.
            end:   (x, y) coordinate tuple representing the ending point.
        """
        self.start = start
        self.end = end

    @abstractmethod
    def __repr__(self):
        pass
    
    def length(self):
        """
        Calculate the length of the object.
        """
        return ((self.end[0] - self.start[0]) ** 2 + (self.end[1] - self.start[1]) ** 2) ** 0.5  # 欧几里得距离
