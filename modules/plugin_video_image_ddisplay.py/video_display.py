import xbmc
import xbmcgui
import xbmcaddon
import os

# Get add-on instance and path
ADDON = xbmcaddon.Addon()
ADDON_PATH = ADDON.getAddonInfo('path')

# Define the path to your XML layout file.
XML_DIALOG = os.path.join(ADDON_PATH, "MyAddon.xml")
# Define the portrait image path. You can also point this to a remote URL.
IMAGE_PATH = os.path.join(ADDON_PATH, "resources", "media", "portrait.jpg")

class PortraitWindow(xbmcgui.WindowXMLDialog):
    def onInit(self):
        # When the window is initialized, set the image control to display the portrait.
        self.imageControl = self.getControl(1000)
        if self.imageControl:
            self.imageControl.setImage(IMAGE_PATH)

    def onClick(self, controlId):
        # Close the window on any click.
        self.close()

    def onAction(self, action):
        # Also close on any action (like a remote button press).
        self.close()
