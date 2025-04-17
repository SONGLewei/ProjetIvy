from model.wall import Wall

class Vent(Wall):
    def __init__(self, start, end, name, diameter, flow_rate, function,color):
        super().__init__(start, end)
        self.name = name
        self.diameter = diameter
        self.flow_rate = flow_rate
        self.function = function
        self.color = color

    def __repr__(self):
        return (f"Vent({self.start} -> {self.end}, "
                f"name={self.name}, diameter={self.diameter}, "
                f"flow_rate={self.flow_rate}, function={self.function})")