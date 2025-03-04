import os
import json
import subprocess

project_dir = os.getcwd()

vscode_folder = os.path.join(project_dir, ".vscode")
os.makedirs(vscode_folder, exist_ok=True)

# settings.json
settings = {
    "python.defaultInterpreterPath": "${workspaceFolder}/venv/Scripts/python.exe",
    "python.analysis.extraPaths": ["./modules"],
    "editor.tabSize": 4,
    "files.exclude": {"**/__pycache__": True}
}
with open(os.path.join(vscode_folder, "settings.json"), "w", encoding="utf-8") as f:
    json.dump(settings, f, indent=4)

# launch.json
launch = {
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Run GMCampaignDesigner",
            "type": "python",
            "request": "launch",
            "program": "${workspaceFolder}/main_window.py",
            "console": "integratedTerminal"
        }
    ]
}
with open(os.path.join(vscode_folder, "launch.json"), "w", encoding="utf-8") as f:
    json.dump(launch, f, indent=4)

# extensions.json
extensions = {
    "recommendations": [
        "ms-python.python",
        "ms-python.vscode-pylance",
        "njpwerner.autodocstring"
    ]
}
with open(os.path.join(vscode_folder, "extensions.json"), "w", encoding="utf-8") as f:
    json.dump(extensions, f, indent=4)

# Create virtual environment
subprocess.run(["python", "-m", "venv", "venv"])

# Install dependencies
subprocess.run(["venv\\Scripts\\activate.bat", "&&", "pip", "install", "customtkinter"], shell=True)

# Generate requirements.txt
subprocess.run(["venv\\Scripts\\activate.bat", "&&", "pip", "freeze", ">", "requirements.txt"], shell=True)

print("✅ VSCode setup complete! Open your project in VSCode and you are ready.")
