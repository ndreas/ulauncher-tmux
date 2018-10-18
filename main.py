import subprocess

from ulauncher.api.client.Extension import Extension
from ulauncher.api.client.EventListener import EventListener
from ulauncher.api.shared.event import KeywordQueryEvent, PreferencesEvent, PreferencesUpdateEvent
from ulauncher.api.shared.item.ExtensionResultItem import ExtensionResultItem
from ulauncher.api.shared.action.RenderResultListAction import RenderResultListAction
from ulauncher.api.shared.action.RunScriptAction import RunScriptAction


class TmuxExtension(Extension):
    def __init__(self):
        super(TmuxExtension, self).__init__()

        self.sessions = None
        self.attach_cmd = 'xterm -e tmux'
        self.sockets = []

        self.subscribe(KeywordQueryEvent, KeywordQueryEventListener())
        self.subscribe(PreferencesEvent, PreferencesEventListener())
        self.subscribe(PreferencesUpdateEvent,
                       PreferencesUpdateEventListener())

    def load_sessions(self):
        self.sessions = tmux_sessions()
        for sock in self.sockets:
            self.sessions += tmux_sessions(sock)

    def build_result(self, session):
        sock_flag = ''

        if session['socket'] is not None:
            sock_flag = '-L {}'.format(session['socket'])

        cmd = '{} {} attach-session -t {}'.format(
            self.attach_cmd,
            sock_flag,
            session['session']
        )

        return ExtensionResultItem(icon='images/icon.png',
                                   name=session['title'],
                                   description=session['description'],
                                   on_enter=RunScriptAction(cmd, None))


class KeywordQueryEventListener(EventListener):
    def on_event(self, event, extension):
        sessions = []
        arg = event.get_argument()

        if extension.sessions is None or arg is None:
            extension.load_sessions()

        sessions = extension.sessions

        if arg is not None:
            arg = arg.lower()
            sessions = filter(lambda s: arg in s['search'], sessions)

        return RenderResultListAction(map(extension.build_result, sessions))


class PreferencesEventListener(EventListener):
    def on_event(self, event, extension):
        extension.attach_cmd = event.preferences['tmux_attach_cmd']
        extension.sockets = event.preferences['tmux_sockets'].split()


class PreferencesUpdateEventListener(EventListener):
    def on_event(self, event, extension):
        if event.id == 'tmux_attach_cmd':
            extension.attach_cmd = event.new_value
        elif event.id == 'tmux_sockets':
            extension.sockets = event.new_value.split()


def tmux_sessions(socket_name=None):
    cmd = [
        'tmux',
        'list-panes',
        '-a',
        '-F#{window_active}#{pane_active}:#{session_attached}:#{session_name}:#{pane_title}'
    ]

    if socket_name is not None:
        cmd.insert(1, '-L')
        cmd.insert(2, socket_name)

    out = ""
    try:
        out = subprocess.check_output(cmd)
    except:
        pass

    sessions = []

    for l in out.splitlines():
        active, attached, session_name, title = l.split(b':', 3)

        title = title.decode('UTF-8')
        if attached == b'0':
            title = '(Detached) {}'.format(title)

        description = 'Session {}'.format(session_name)
        search = '{} {}'.format(
            title.lower(),
            session_name.lower(),
        )

        if active == b'11':
            sessions.append({
                'socket':      socket_name,
                'session':     session_name,
                'title':       title,
                'description': description,
                'search':      search
            })

    return sessions


if __name__ == '__main__':
    TmuxExtension().run()
