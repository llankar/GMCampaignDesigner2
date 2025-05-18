import sys, time
from pywinauto import Application, Desktop, timings

# 1. Build cmd exactly as before
pythonw = sys.executable.replace("python.exe", "pythonw.exe")
script = r"D:\SynologyDrive\rpg\Python\GMCampaignDesigner2\main_window.py"
cmd = f'"{pythonw}" "{script}"'

# 2. Start the app (UIA backend)
app = Application(backend="uia").start(cmd, wait_for_idle=False)

# 3. Give it a second to pop up
time.sleep(1)

# 4. Debug: print every top-level window
print("All UIA windows:")
for w in Desktop(backend="uia").windows():
    print(" •", repr(w.window_text()), "(", w.class_name(), ")")

# 5. Now attach using whatever you saw above.
#    Suppose the title really is "GMCampaignDesigner" exactly:
dlg = app.window(title="MainWindowView")

# 6. Wait explicitly for that window
dlg.wait("visible enabled ready", timeout=20)

# 7. You can now interact:
dlg.print_control_identifiers()