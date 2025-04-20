from model.wall import Wall

class Window(Wall):
    def __init__(self, start, end, thickness=3):
        """
        Create a Window object, similar to a wall but with a different thickness.
        """
        super().__init__(start, end)
        self.thickness = thickness

    def __repr__(self):
        return f"Window({self.start} -> {self.end}, orientation={self.orientation}, length={self.length()}, thickness={self.thickness})"
    
    def to_dict(self):
        return {"start": self.start, "end": self.end, "thickness": self.thickness}