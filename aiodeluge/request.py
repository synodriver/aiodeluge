"""
Copyright (c) 2008-2022 synodriver <synodriver@gmail.com>
"""


def format_kwargs(kwargs):
    return ", ".join([key + "=" + str(value) for key, value in kwargs.items()])


class DelugeRPCRequest:
    """
    This object is created whenever there is a RPCRequest to be sent to the
    daemon.  It is generally only used by the DaemonProxy's call method.
    """

    request_id = None
    method = None
    args = None
    kwargs = None

    def __repr__(self):
        """
        Returns a string of the RPCRequest in the following form:
            method(arg, kwarg=foo, ...)
        """
        s = self.method + "("
        if self.args:
            s += ", ".join([str(x) for x in self.args])
        if self.kwargs:
            if self.args:
                s += ", "
            s += format_kwargs(self.kwargs)
        s += ")"

        return s

    def format_message(self):
        """
        Returns a properly formatted RPCRequest based on the properties.  Will
        raise a TypeError if the properties haven't been set yet.
        :returns: a properly formatted RPCRequest
        """
        if (
            self.request_id is None
            or self.method is None
            or self.args is None
            or self.kwargs is None
        ):
            raise TypeError(
                "You must set the properties of this object before calling format_message!"
            )

        return self.request_id, self.method, self.args, self.kwargs
