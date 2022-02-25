#!/usr/bin/python3
"""A KRunner plugin to open zoom meetings from a saved list or directly using the meeting id."""

from pathlib import Path
from configparser import ConfigParser
from os import system

import dbus
import dbus.service
from dbus.mainloop.glib import DBusGMainLoop
from gi.repository import GLib

KEY_WORD = "zm"
MAX_RESULTS = 13


icon_path = str(Path.joinpath(Path.cwd(), "assets", "icon.png"))

DBusGMainLoop(set_as_default=True)

objpath = "/krunnerZoom"

iface = "org.kde.krunner1"


def get_opener_path() -> str:
    """Find the opening utility path."""
    openers_list = ["/usr/bin/xdg-open", "/usr/bin/open"]
    for opener in openers_list:
        if Path.exists(Path(opener)):
            return opener
    raise EnvironmentError("xdg-open utility was not found.")


def get_meetings_list() -> list:
    """Return a list of the saved meetings form an ini file."""
    meetings: list = []

    config = ConfigParser()
    config.read(Path.joinpath(Path.home(), ".zoom_meetings_runner"))

    for meeting in config.sections():
        if not meeting.startswith("meeting_"):
            continue

        try:
            meeting_name = config[meeting]["name"]
        except KeyError:
            meeting_name = "Undefined"

        try:
            meeting_id = config[meeting]["id"]
        except KeyError:
            continue

        try:
            meeting_passcode = config[meeting]["passcode"]
        except KeyError:
            meeting_passcode = None

        meetings.append(
            {
                "section": meeting,
                "name": meeting_name,
                "id": meeting_id,
                "passcode": meeting_passcode,
            }
        )

    return meetings


def create_temp_meeting(meeting_id: str, passcode: str = None):
    """Create a temp meeting to be joined directly in the session witout saveing it."""
    return {
        "section": "temp_metting",
        "name": meeting_id,
        "id": meeting_id,
        "passcode": passcode,
    }


class Runner(dbus.service.Object):
    """Comunicate with KRunner, load the config file and metch the queries."""

    def __init__(self) -> None:
        """Get opener path and load meetings list."""
        dbus.service.Object.__init__(
            self,
            dbus.service.BusName("com.github.zer0-x.krunner-zoom", dbus.SessionBus()),
            objpath,
        )

        self.opener_path = get_opener_path()
        self.meetings = get_meetings_list()

        # Connet to klipper to use the clipboard.
        self.bus = dbus.SessionBus()
        self.klipper_iface = dbus.Interface(
            self.bus.get_object("org.kde.klipper", "/klipper"), "org.kde.klipper.klipper"
        )

        return None

    @dbus.service.method(iface, in_signature="s", out_signature="a(sssida{sv})")
    def Match(self, query: str):
        """Get the matches and return a list of tupels."""
        returns: list = []

        if query.startswith(KEY_WORD):
            query = query[3:]

            if query == "update":
                self.meetings = get_meetings_list()
                return [
                    (
                        "",
                        "Meetings list has been loaded successfully.",
                        icon_path,
                        100,
                        1.0,
                        {},
                    )
                ]

            try:
                assert int(query)
            except Exception:
                pass
            else:
                self.temp_metting = create_temp_meeting(query)
                returns.append(
                    (
                        "temp_metting",
                        f"Join meeting with id: {query}",
                        icon_path,
                        100,
                        1.0,
                        {},
                    )
                )

            for meeting in self.meetings:
                if query in meeting["name"].lower():
                    # data, display text, icon, type (Plasma::QueryType), relevance (0-1), properties (subtext, category and urls)
                    returns.append(
                        (
                            meeting["section"],
                            meeting["name"],
                            icon_path,
                            100,
                            1.0,
                            {},
                        )
                    )

            return returns[:MAX_RESULTS]
        else:
            return []

    @dbus.service.method(iface, out_signature="a(sss)")
    def Actions(self):
        """Return a list of actions."""
        return [
            # id, text, icon
            ("0", "Copy meeting id", "edit-copy"),
            ("1", "Copy meeting passcode", "password-copy"),
            ("2", "Copy meeting uri", "gnumeric-link-url"),
        ]

    @dbus.service.method(iface, in_signature="ss")
    def Run(self, data: str, action_id: str):
        """Handle actions calls."""
        if data == "":
            return None
        elif data == "temp_metting":
            meeting_data = self.temp_metting
        else:
            for meeting_data in self.meetings:
                if meeting_data["section"] == data:
                    break

        meeting_uri = (f"zoommtg://zoom.us/join?action=join&confno={meeting_data['id']}"
                       + ('&pwd=' + meeting_data['passcode'] if meeting_data['passcode'] else ""))

        if action_id == "":
            system(f"{self.opener_path} {meeting_uri}")
        elif action_id == "0":
            self.klipper_iface.setClipboardContents(meeting_data["id"])
            pass
        elif action_id == "1":
            try:
                self.klipper_iface.setClipboardContents(meeting_data["passcode"])
            except Exception:
                pass
        elif action_id == "2":
            self.klipper_iface.setClipboardContents("https" + meeting_uri[7:])
            pass


runner = Runner()
loop = GLib.MainLoop()
loop.run()
