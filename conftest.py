
def pytest_addoption(parser):
    group = parser.getgroup("Kivy")
    group._addoption('--record',
               action="store_true", dest="kivy_record", default=False,
               help="Keep widget at end of test and print events")

    group = parser.getgroup("Kivy")
    group._addoption('--noanim',
               action="store_true", dest="kivy_noanim", default=False,
               help="Make all animations finninsh in one frame")
