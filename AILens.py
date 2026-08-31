from microbit import *

Camera_Add = 0x14
Card = 2
Face = 6
Ball = 7
Tracking = 8
Color = 9
Learn = 10
numberCards = ["0", "1", "2", "3", "4", "5", "6", "7", "8", "9"]
letterCards = ["A", "B", "C", "D", "E"]
otherCards = ["Mouse", "micro:bit", "Ruler", "Cat", "Peer", "Ship", "Apple", "Car", "Pan", "Dog", "Umbrella",
              "Airplane", "Clock", "Grape", "Cup", "Turn left", "Turn right", "Forward", "Stop", "Back"]
colorList = ["Green", "Blue", "Yellow", "Black", "Red", "White"]


class AILENS(object):
    """AI Lens smart camera module (ELECFREAKS 'Erlang Shen' AI camera).
    """

    def __init__(self):
        self.__Data_buff = [0, 0, 0, 0, 0, 0, 0, 0, 0]
        i2c.init()
        sleep(5000)
        try:
            i2c.read(Camera_Add, 1)
        except OSError:
            display.scroll("Init AILens Error!")

    def switch_function(self, func):
        """Select the camera function mode.

        :param func: function ID to activate (Card, Face, Ball, Tracking, Color or Learn)
        """
        i2c.write(Camera_Add, bytearray([0x20, func]))

    def get_image(self):
        """Read one frame of image data from the camera.

        :return: current frame data (stored in the internal buffer)
        """

        self.__Data_buff = i2c.read(Camera_Add, 9)
        sleep(100)

    def get_ball_color(self):
        """Detect the color of the ball in the current frame.

        :return: "Blue", "Red" or "No Ball"
        """
        if self.__Data_buff[0] == 7:
            if self.__Data_buff[1] == 1:
                return "Blue"
            elif self.__Data_buff[1] == 2:
                return "Red"
        else:
            return "No Ball"

    def get_ball_data(self):
        """Return information about the ball in the current frame.

        :return: BallData [x,y,w,h,confidence,total,order]
        """
        BallData = []
        for i in range(7):
            BallData.append(self.__Data_buff[i + 2])
        return BallData

    def get_face(self):
        """Check whether a face is present in the current frame.

        :return: True if a face is detected
        """
        return self.__Data_buff[0] == 6

    def get_face_data(self):
        """Return information about the face in the current frame.

        :return: FaceData [x,y,w,h,confidence,total,order]
        """
        FaceData = []
        for i in range(7):
            FaceData.append(self.__Data_buff[i + 2])
        return FaceData

    def get_card_content(self):
        """Return the content of the recognized card in the current frame.

        :return: card content as a string
        """
        if self.__Data_buff[0] == 2:
            return numberCards[self.__Data_buff[1] - 1]
        elif self.__Data_buff[0] == 4:
            return letterCards[self.__Data_buff[1] - 1]
        elif self.__Data_buff[0] == 3 and self.__Data_buff[1] < 21:
            return otherCards[self.__Data_buff[1] - 1]
        else:
            return "No Card"

    def get_card_data(self):
        """Return information about the card in the current frame.

        :return: CardData [x,y,w,h,confidence,total,order]
        """
        CardData = []
        for i in range(7):
            CardData.append(self.__Data_buff[i + 2])
        return CardData

    def get_color_type(self):
        """Return the detected color in the current frame.

        :return: color name
        """
        if self.__Data_buff[0] == 9:
            return colorList[self.__Data_buff[1] - 1]
        else:
            return "No Color"

    def get_color_data(self):
        """Return information about the color block in the current frame.

        :return: ColorData [x,y,w,h,confidence,total,order]
        """
        ColorData = []
        for i in range(7):
            ColorData.append(self.__Data_buff[i + 2])
        return ColorData

    def get_track_data(self):
        """Return information about the line segment in the current frame.

        :return: LineData [angel,width,len]
        """
        LineData = []
        for i in range(3):
            LineData.append(self.__Data_buff[i + 1])
        return LineData

    def learn_object(self, learn_id):
        """Learn (train) an object under the given ID.

        :param learn_id: ID number to learn the object as (1-5)
        """
        if learn_id > 5 or learn_id < 1:
            print("Learn id out of range")
        else:
            i2c.write(Camera_Add, bytearray([10, learn_id]))

    def get_learn_data(self):
        """Return information about the learned object in the current frame.

        :return: LearnData [ID,confidence]
        """
        LearnData = [self.__Data_buff[1], 100 - self.__Data_buff[2]]
        return LearnData