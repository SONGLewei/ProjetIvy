class Plenum:
    def __init__(self, start, end, max_flow=1000):
        self.start = start  # (x1, y1)
        self.end = end      # (x2, y2)
        self.max_flow = max_flow
        self.type = None
        
        # Calculate area in square meters
        self.calculate_area()
    
    def calculate_area(self):
        """Calculate the area of the plenum in square meters."""
        # Calculate width and height in pixels
        width_px = abs(self.end[0] - self.start[0])
        height_px = abs(self.end[1] - self.start[1])
        
        # Convert to meters based on scale (40px = 2m)
        width_m = width_px * (2.0/40.0)
        height_m = height_px * (2.0/40.0)
        
        # Calculate area in square meters with 2 decimal places
        self.area = round(width_m * height_m, 2)
        return self.area

    def to_dict(self):
        return {
            "start": self.start,
            "end": self.end,
            "max_flow": self.max_flow,
            "type": self.type,
            "area": self.area
        }
    
    @staticmethod
    def from_dict(data):
        plenum_obj = Plenum(
            start=tuple(data.get("start", (0,0))),
            end=tuple(data.get("end", (0,0))),
            max_flow=data.get("max_flow", 1000)
        )
        plenum_obj.type = data.get("type", None)
        plenum_obj.floor_index = data.get("floor_index")
        plenum_obj.area = data.get("area", plenum_obj.area)  # Use calculated area as fallback

        return plenum_obj

    def __repr__(self):
        return f"Plenum(start={self.start}, end={self.end}, max_flow={self.max_flow}, area={self.area}m²)"
