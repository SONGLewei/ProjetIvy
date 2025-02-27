class Wall:
    def __init__(self, start, end):
        """
        Create a wall object.
        
        Parameters:
            start: (x, y) coordinate tuple representing the starting point of the wall.
            end:   (x, y) coordinate tuple representing the ending point of the wall.
        
        To ensure that the wall is either horizontal or vertical, 
        its orientation is determined based on the larger difference between the two coordinates.
        The endpoint is then adjusted to align with the start point in either the horizontal or vertical direction.
        """
        self.start = start
        self.end = end
        self.orientation = self._determine_orientation()

        if self.orientation == "horizontal":
            self.end = (end[0], start[1])
        else:
            self.end = (start[0], end[1])
    
    def _determine_orientation(self):
        """
        Determine the orientation of the wall based on the difference between two points:
            - If the horizontal distance is greater than or equal to the vertical distance, the wall is considered horizontal.
            - Otherwise, the wall is considered vertical.
        """
        dx = abs(self.end[0] - self.start[0])
        dy = abs(self.end[1] - self.start[1])
        return "horizontal" if dx >= dy else "vertical"

    def length(self):
        """
        Return the length of the wall, calculated based on its orientation.
        """
        if self.orientation == "horizontal":
            return abs(self.end[0] - self.start[0])
        else:
            return abs(self.end[1] - self.start[1])

    def __repr__(self):
        return f"Wall({self.start} -> {self.end}, orientation={self.orientation}, length={self.length()})"
