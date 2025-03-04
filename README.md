GMCampaignDesigner2
GMCampaignDesigner2 is an open-source tool designed to help game masters design, organize, and manage their campaigns. Built in Python, the project provides a modular framework for handling various aspects of campaign design—from mapping and NPC management to tracking events and storylines.

Overview
GMCampaignDesigner2 is aimed at enhancing the creative process for game masters by offering an easy-to-use platform that consolidates essential campaign planning tools. The project is structured to be extensible, making it easy to add new features or customize existing ones.

Features
Campaign Management: Organize campaigns by chapters or story arcs with detailed timelines.
NPC and Character Handling: Create, edit, and manage non-player characters (NPCs) with custom attributes.
Map Integration: Tools for designing, annotating, and linking maps to campaign events.
Event Scheduling: Manage key events, encounters, and storyline milestones.
Modular Architecture: Structured in separate Python modules for ease of maintenance and future expansion.
Open Source: Licensed under GPL-3.0, encouraging community contributions and collaboration.
Installation
Prerequisites
Python 3.8+ – Ensure you have Python installed.
Other dependencies are listed in the requirements.txt file.
Steps
Clone the Repository:

bash
Copier
git clone https://github.com/llankar/GMCampaignDesigner2.git
cd GMCampaignDesigner2
Install Dependencies:

bash
Copier
pip install -r requirements.txt
Run the Application:

bash
Copier
python main.py
Note: If requirements.txt is not yet available, please install any dependencies manually as the project develops.

Usage
Upon launching the application, you will be greeted with a command-line interface (CLI) that allows you to:

Create a New Campaign: Set up your campaign details.
Manage NPCs: Add and modify NPC information.
Design Maps: Open the map editor to draft and annotate your campaign world.
Schedule Events: Track and plan key events throughout your campaign.
The tool is designed to be interactive, with on-screen prompts guiding you through each process.

Project Structure
The project is organized into several Python modules, each handling a specific aspect of campaign design:

main.py
The entry point of the application that ties all modules together and launches the CLI.

campaign.py
Contains functions and classes to manage campaign data, including creation, editing, and storage of campaign elements.

npcs.py
Manages the creation and manipulation of non-player characters. This module can be extended to include detailed character attributes and relationships.

maps.py
Provides tools to design, annotate, and manage maps related to your campaign. Future versions may include integration with graphical libraries for advanced map editing.

events.py
Handles scheduling and tracking of campaign events. Use this module to set up timelines and encounter logs.

utils.py
A collection of utility functions that support the functionality of other modules.

Disclaimer: The current implementation of these modules might be minimal as the project is in early development. Contributions are welcome to expand functionality or improve existing features.

Contributing
Contributions to GMCampaignDesigner2 are highly encouraged! If you’d like to contribute, please follow these steps:

Fork the repository.
Create a new branch for your feature or bug fix.
Commit your changes and open a pull request.
Follow the guidelines provided in the CONTRIBUTING.md file (if available).
Please open an issue first if you are planning a major change to discuss your ideas.

License
GMCampaignDesigner2 is licensed under the GPL-3.0 License. See the LICENSE file for details.
