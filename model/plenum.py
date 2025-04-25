class Plenum:
    def __init__(self, start, end, max_flow=1000):
        self.start = start  # (x1, y1)
        self.end = end      # (x2, y2)
        self.max_flow = max_flow
        self.type   = None 

    def to_dict(self):
        return {
            "start": self.start,
            "end": self.end,
            "max_flow": self.max_flow,
            "type": self.type
        }
    
    @staticmethod
    def from_dict(data):
        plenum_obj =  Plenum(
            start=tuple(data.get("start", (0,0))),
            end=tuple(data.get("end", (0,0))),
            max_flow=data.get("max_flow", 1000)
        )
        plenum_obj.type = data.get("type", None)
        plenum_obj.floor_index = data.get("floor_index")

        return plenum_obj

    def __repr__(self):
        return f"Plenum(start={self.start}, end={self.end}, max_flow={self.max_flow})"
