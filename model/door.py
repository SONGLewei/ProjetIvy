from model.wall import Wall

class Door(Wall):
    def __init__(self,start,end,thickness=5):
        super().__init__(start,end)
        self.thickness = thickness
        
    def __repr__(self):
        return f"Door({self.start} -> {self.end}, orientation={self.orientation}, length={self.length()}, thickness={self.thickness})"
    
    def to_dict(self):
        return {"start": self.start, "end": self.end}
