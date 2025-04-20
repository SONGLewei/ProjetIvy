from view.graphical_view import GraphicalView
from controller.controller import Controller

def main():
    controller = Controller()
    app = GraphicalView()
    controller.attach_view(app)
    app.mainloop()


if __name__ == "__main__":
    main()
