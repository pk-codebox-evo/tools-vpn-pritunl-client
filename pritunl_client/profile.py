from constants import *
from exceptions import *
import os
import uuid
import json
import time
import gobject

_connections = {}

class Profile:
    def __init__(self, id=None):
        if id:
            self.id = id
        else:
            self.id = uuid.uuid4().hex
        self._loaded = False

        self.profile_name = None
        self.user_name = None
        self.org_name = None
        self.server_name = None
        self.autostart = False

        if not os.path.isdir(PROFILES_DIR):
            os.makedirs(PROFILES_DIR)

        self.path = os.path.join(PROFILES_DIR, '%s.ovpn' % self.id)
        self.conf_path = os.path.join(PROFILES_DIR, '%s.conf' % self.id)

        if id:
            self.load()

    def __getattr__(self, name):
        if name == 'name':
            if self.profile_name:
                return self.profile_name
            elif self.user_name and self.org_name and self.server_name:
                return '%s@%s (%s)' % (self.user_name, self.org_name,
                    self.server_name)
            else:
                return 'Unknown Profile'
        elif name == 'status':
            connection_data = _connections.get(self.id)
            if connection_data:
                return connection_data.get('status', ENDED)
            return ENDED
        elif name not in self.__dict__:
            raise AttributeError('Config instance has no attribute %r' % name)
        return self.__dict__[name]

    def load(self):
        if os.path.exists(self.conf_path):
            with open(self.conf_path, 'r') as conf_file:
                data = json.loads(conf_file.read())
                self.profile_name = data.get('name')
                self.user_name = data.get('user')
                self.org_name = data.get('organization')
                self.server_name = data.get('server')
                self.autostart = data.get('autostart') or False

    def commit(self):
        with open(self.conf_path, 'w') as conf_file:
            conf_file.write(json.dumps({
                'name': self.profile_name,
                'user': self.user_name,
                'organization': self.org_name,
                'server': self.server_name,
                'autostart': self.autostart,
            }))

    def _parse_profile(self, data):
        conf_str = data.splitlines()[0].replace('#', '', 1).strip()
        profile_data = data
        try:
            conf_data = json.loads(conf_str)
            profile_data = '\n'.join(profile_data.splitlines()[1:])
        except ValueError:
            conf_data = {}
        return conf_data, profile_data

    def write_profile(self, data, default_name='Unknown Profile'):
        conf_data, profile_data = self._parse_profile(data)
        self.profile_name = conf_data.get('name')
        self.user_name = conf_data.get('user')
        self.org_name = conf_data.get('organization')
        self.server_name = conf_data.get('server')
        self.autostart = conf_data.get('autostart') or False
        self.commit()
        with open(self.path, 'w') as profile_file:
            os.chmod(self.path, 0600)
            profile_file.write(profile_data)

    def set_name(self, name):
        self.profile_name = name
        self.commit()

    def set_autostart(self, state):
        self.autostart = state
        self.commit()

    def delete(self):
        self.stop()
        if os.path.exists(self.path):
            os.remove(self.path)
        if os.path.exists(self.conf_path):
            os.remove(self.conf_path)

    def _set_status(self, status):
        data = _connections.get(self.id)
        if not data:
            return
        data['status'] = status
        callback = data.get('connect_callback')
        if callback:
            data['connect_callback'] = None
            gobject.idle_add(callback)

        callback = data.get('status_callback')
        if callback:
            gobject.idle_add(callback)

    def start(self, status_callback, connect_callback=None):
        if self.status not in (DISCONNECTED, ENDED):
            self._set_status(self.status)
            return
        self._start(status_callback, connect_callback)

    def start_autostart(self, status_callback, connect_callback=None):
        if self.status not in (DISCONNECTED, ENDED):
            return
        self._start_autostart(status_callback, connect_callback)

    def _start(self, status_callback, connect_callback=None):
        raise NotImplementedError()

    def stop(self):
        self._stop()

    def _stop(self):
        raise NotImplementedError()

    @classmethod
    def iter_profiles(cls):
        if os.path.isdir(PROFILES_DIR):
            for profile_path in os.listdir(PROFILES_DIR):
                profile_id, extension = os.path.splitext(profile_path)
                if extension == '.ovpn':
                    yield cls.get_profile(profile_id)

    @classmethod
    def get_profile(cls, id=None):
        from profile_linux import ProfileLinux
        from profile_win import ProfileWin
        from profile_osx import ProfileOsx
        if PLATFORM == LINUX:
            return ProfileLinux(id)
        elif PLATFORM == WIN:
            return ProfileWin(id)
        elif PLATFORM == OSX:
            return ProfileOsx(id)
