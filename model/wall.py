from model.object import Object

class Wall(Object):
    def __init__(self, start, end):
        """
        Create a wall object.
        """
        super().__init__(start, end)
        self.orientation = self._determine_orientation()

        if self.orientation == "horizontal":
            self.end = (end[0], start[1])
        else:
            self.end = (start[0], end[1])
    
    def _determine_orientation(self):
        """
        Determine the orientation of the wall based on the difference between two points.
        """
        dx = abs(self.end[0] - self.start[0])
        dy = abs(self.end[1] - self.start[1])
        return "horizontal" if dx >= dy else "vertical"

    def __repr__(self):
        return f"Wall({self.start} -> {self.end}, orientation={self.orientation}, length={self.length()})"
