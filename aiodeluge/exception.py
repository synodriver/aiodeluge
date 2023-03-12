"""
Copyright (c) 2008-2022 synodriver <synodriver@gmail.com>
"""
class DelugeError(Exception):
    def __new__(cls, *args, **kwargs):
        inst = super().__new__(cls, *args, **kwargs)
        inst._args = args
        inst._kwargs = kwargs
        return inst

    def __init__(self, message=None):
        super().__init__(message)
        self.message = message

    def __str__(self):
        return self.message


class DaemonRunningError(DelugeError):
    pass


class InvalidTorrentError(DelugeError):
    pass


class AddTorrentError(DelugeError):
    pass


class InvalidPathError(DelugeError):
    pass


class WrappedException(DelugeError):
    def __init__(self, message, exception_type, traceback):
        super().__init__(message)
        self.type = exception_type
        self.traceback = traceback

    def __str__(self):
        return f'{self.message}\n{self.traceback}'


class _ClientSideRecreateError(DelugeError):
    pass


class IncompatibleClient(_ClientSideRecreateError):
    def __init__(self, daemon_version):
        self.daemon_version = daemon_version
        msg = (
            'Your deluge client is not compatible with the daemon. '
            'Please upgrade your client to %(daemon_version)s'
        ) % {'daemon_version': self.daemon_version}
        super().__init__(message=msg)


class NotAuthorizedError(_ClientSideRecreateError):
    def __init__(self, current_level, required_level):
        msg = ('Auth level too low: %(current_level)s < %(required_level)s') % {
            'current_level': current_level,
            'required_level': required_level,
        }
        super().__init__(message=msg)
        self.current_level = current_level
        self.required_level = required_level


class _UsernameBasedPasstroughError(_ClientSideRecreateError):
    def __init__(self, message, username):
        super().__init__(message)
        self.username = username


class BadLoginError(_UsernameBasedPasstroughError):
    pass


class AuthenticationRequired(_UsernameBasedPasstroughError):
    pass


class AuthManagerError(_UsernameBasedPasstroughError):
    pass


class LibtorrentImportError(ImportError):
    pass