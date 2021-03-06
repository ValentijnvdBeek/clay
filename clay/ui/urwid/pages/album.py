"""
Components for " playlists" page.
"""
import urwid

from .page import AbstractPage, AbstractListBox, AbstractListItem
from clay.core import gp
from clay.ui.urwid import SongListBox


class AlbumListBox(AbstractListBox):
    """
    List of playlists.
    """

    def __init__(self, app, icon):
        super(AlbumListBox, self).__init__(app, icon)

    def populate(self, albums):
        items = []
        for album in sorted(albums, key=albums.__getitem__):
            album = AbstractListItem(albums[album], self._icon)
            urwid.connect_signal(album, 'activate', self.item_activated)
            items.append(album)
        self.walker[:] = items
        self.app.redraw()

    def auth_state_changed(self, is_auth):
        """
        Called when auth state changes (e. g. user is logged in).
        Requests fetching of playlists.
        """
        if is_auth:
            self.walker[:] = [
                urwid.Text(u'\n \uf01e Loading albums...', align='center')
            ]
            gp.cached_albums


class AlbumsPage(urwid.Columns, AbstractPage):
    """
    Playlists page.

    Contains two parts:

    - List of playlists (:class:`.PlaylistListBox`)
    - List of songs in selected playlist (:class:`clay:songlist:SongListBox`)
    """
    @property
    def name(self):
        return 'Albums'

    @property
    def key(self):
        return 3

    @property
    def slug(self):
        """
        Return page ID (str).
        """
        return "albums"

    def __init__(self, app):
        self.app = app
        self.albumslist = AlbumListBox(app, '\u2630')
        self.songlist = SongListBox(app)
        self.songlist.set_placeholder('\n Select an album.')

        gp.parsed_songs += self.populate
        gp.caches_invalidated += self.populate

        urwid.connect_signal(
            self.albumslist, 'activate', self.playlist_activated
        )

        super(AlbumsPage, self).__init__([
            self.albumslist,
            self.songlist
        ])

    def populate(self, *_):
        self.albumslist.populate(gp.cached_albums)
        self.app.redraw()

    def playlist_activated(self, album):
        """
        Called when specific playlist is selected.
        Populates songlist with tracks from the selected playlist.
        """
        self.songlist.populate(album.tracks)

    def activate(self):
        pass
