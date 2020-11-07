import os
import time
import logging
import gi
gi.require_version('Gtk', '3.0')
from gi.repository import Wnck, Gtk
from gi.repository.Gdk import CURRENT_TIME

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent, ItemEnterEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.HideWindowAction import HideWindowAction
from ulauncher.api.shared.action.CopyToClipboardAction import CopyToClipboardAction
from ulauncher.api.shared.action.ExtensionCustomAction import ExtensionCustomAction

logger = logging.getLogger(__name__)


class WindowsSwitcherExtension(Extension):

    def __init__(self):
        super(WindowsSwitcherExtension, self).__init__()
        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(ItemEnterEvent, ItemEnterEventListener())


class KeywordQueryEventListener(EventListener):

    def on_event(self, event, extension):
        indicator = extension.preferences['workspace_indicator']
        self.workspace_indicator = True if indicator == 'true' else False

        items = []

        for window in get_active_windows():
            if window.get_class_group_name() == 'Ulauncher':
                continue

            query = event.get_argument()
            if not query or self.is_name_in_query(window, query):
                items.append(self.create_result_item(window))

        return RenderResultListAction(items)

    def is_name_in_query(self, window, query):
        # TODO implement fuzzy search
        full_name = (window.get_name() + window.get_class_group_name()
                     ).decode('utf-8').lower()
        return query.decode('utf-8').lower() in full_name

    def create_result_item(self, window):
        # icon as Pixbuf is not supported; saving it on the disk as a workaround
        icon = window.get_icon()
        icon_name = window.get_class_group_name()
        icon_type = 'ico'
        icon_path = '/tmp/{}.{}'.format(icon_name, icon_type)

        window_desc = window.get_name()

        if self.workspace_indicator:
            window_desc = '({}) {}'.format(window.workspace_id, window_desc)

        if not os.path.exists(icon_path):
            save_result = icon.savev(icon_path, icon_type, [], [])
            if not save_result:
                logger.error(
                    'Unable to write to /tmp. Using default icon as a fallback.')
                icon_path = 'images/switch.png'

        return ExtensionResultItem(
            icon=icon_path,
            name=window.get_class_group_name(),
            description=window_desc,
            on_enter=ExtensionCustomAction({'xid': window.get_xid()}))


class ItemEnterEventListener(EventListener):

    def on_event(self, event, extension):
        data = event.get_data()

        # have to fetch active windows again, passing window in data not supported
        windows = get_active_windows()

        try:
            window = next(w for w in windows if w.get_xid() == data['xid'])

            # fallback in case next line doesn't work
            window.activate(time.time())

            # set focus by activiating with timestamp of 0;
            # Wnck gives a warning but otherwise seems to work
            window.activate(CURRENT_TIME)
        except:
            logger.error('Application not accessible')


def get_active_windows():
    Gtk.init([])  # necessary only if not using a Gtk.main() loop

    screen = Wnck.Screen.get_default()
    screen.force_update()  # recommended per Wnck documentation

    windows = screen.get_windows_stacked()
    for i, window in enumerate(windows):
        try:
            window.workspace_id = window.get_workspace().get_number() + 1
        except AttributeError:
            logger.debug("A window ({}) is not attached to any workspace".format(window.get_name()))
            # remove the window from the list to avoid NoneType on workspace_id
            del(windows[i])

    # clean up Wnck (saves resources, check documentation)
    screen = None
    Wnck.shutdown()

    return windows


if __name__ == '__main__':
    WindowsSwitcherExtension().run()
