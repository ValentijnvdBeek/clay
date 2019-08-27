"""
Components for song listing.
"""
from enum import Enum
import urwid

from clay.core import gp, settings_manager
from clay.playback.player import get_player

from .notifications import notification_area
from .hotkeys import hotkey_manager
from .clipboard import copy
from .variables import States, Icons

player = get_player()


class _Line1:
    _attributes = {
        States.idle: ('line1', 'line1_focus'),
        States.loading: ('line1_active', 'line1_active_focus'),
        States.playing: ('line1_active', 'line1_active_focus'),
        States.paused: ('line1_active', 'line1_active_focus')
    }

    def __init__(self):
        self._left = urwid.SelectableIcon('', cursor_position=1000)
        self._left.set_layout('left', 'clip', None)
        self._right = urwid.Text('x')
        self._content = urwid.Columns([
            self._left,
            ('pack', self._right),
            ('pack', urwid.Text(' '))
        ])
        self._wrap = urwid.AttrWrap(self._content, 'line1')

    def update_text(self, track):
        self._left.set_text(
            u'{index:3d} {icon} {title} [{minutes:02d}:{seconds:02d}]'.format(
                index=track.index + 1,
                icon=track.get_state_icon(track.state),
                title=track.track.title,
                minutes=track.track.duration // (1000 * 60),
                seconds=(track.track.duration // 1000) % 60,
            )
        )

        if settings_manager.get_is_file_cached(track.track.filename):
            self._right.set_text(u' \u25bc Cached')
        else:
            self._right.set_text(u'')

        self._right.set_text(u'{explicit} {rating}'.format(explicit=track.explicit, rating=track.rating))

        self._wrap.set_attr(self._attributes[track.state][track.is_focused])


class _Line2:
    _attributes = {
        States.idle: ('line2', 'line2_focus'),
        States.loading: ('line2', 'line2_focus'),
        States.playing: ('line2', 'line2_focus'),
        States.paused: ('line2', 'line2_focus'),
    }

    def __init__(self):
        self._content = urwid.Text('', wrap='clip')
        self._wrap = urwid.AttrWrap(self._content, 'line2')

    def update_text(self, track):
        self._content.set_text(u'      {} \u2015 {}'.format(track.track.artist, track.track.album_name))
        self._wrap.set_attr(self._attributes[track.state][track.is_focused])


class SongListItem(urwid.Pile):
    """
    Widget that represents single song item.
    """
    _unicode = settings_manager.get('unicode', 'clay_settings')
    signals = [
        'activate',
        'play',
        'append-requested',
        'unappend-requested',
        'clear-queue',
        'station-requested',
        'context-menu-requested'
    ]

    def __init__(self, track):
        self.track = track
        self.rating = Icons.ratings[track.rating]
        self.explicit = Icons.explicit[track.explicit_rating]
        self.index = 0
        self.state = States.idle
        self.line1 = _Line1()
        self.line2 = _Line2()

        self.content = urwid.Pile([
            self.line1._wrap,
            self.line2._wrap,
            urwid.Text('')
        ])

        self.is_focused = False

        super(SongListItem, self).__init__([
            self.content
        ])
        self.update_text()

    def set_state(self, state):
        """
        Set state for this song.
        Possible choices are:

        - :attr:`States.idle`
        - :attr:`States.loading`
        - :attr:`States.playing`
        - :attr:`States.paused`
        """
        self.state = state
        self.update_text()

    @staticmethod
    def get_state_icon(state):
        """
        Get icon char for specific state.
        """
        return Icons.state[state.value]

    def update_text(self):
        """
        Update text of this item from the attached track.
        """
        self.line1.update_text(self)
        self.line2.update_text(self)

    @property
    def full_title(self):
        """
        Return song artist and title.
        """
        return u'{} - {} {}'.format(
            self.track.artist,
            self.track.title,
            self.rating
        )

    def keypress(self, size, key):
        """
        Handle keypress.
        """
        return hotkey_manager.keypress("song_item", self, super(SongListItem, self), size, key)

    def mouse_event(self, size, event, button, col, row, focus):
        """
        Handle mouse event.
        """
        if button == 1 and focus:
            urwid.emit_signal(self, 'activate', self)
            return None
        return super(SongListItem, self).mouse_event(size, event, button, col, row, focus)

    def thumbs_up(self):
        """
        Thumb the currently selected song up.
        """
        self.track.rate_song((0 if self.track.rating == 5 else 5))

    def thumbs_down(self):
        """
        Thumb the currently selected song down.
        """
        self.track.rate_song((0 if self.track.rating == 1 else 1))

    def _send_signal(self, signal):
        urwid.emit_signal(self, signal, self)

    def activate(self):
        """
        Add the entire list to queue and begin playing
        """
        self._send_signal("activate")

    def clear_queue(self):
        """
        Removes all the songs from the queue.
        """
        self.set_state(States.idle)
        self.is_focused = False
        self._send_signal("clear-queue")

    def play(self):
        """
        Play this song.
        """
        self._send_signal("play")

    def append(self):
        """
        Add this song to the queue.
        """
        self._send_signal("append-requested")

    def unappend(self):
        """
        Remove this song from the queue.
        """
        if not self.is_currently_played:
            self._send_signal("unappend-requested")

    def request_station(self):
        """
        Create a Google Play Music radio for this song.
        """
        self._send_signal("station-requested")

    def show_context_menu(self):
        """
        Display the context menu for this song.
        """
        self._send_signal("context-menu-requested")

    @property
    def is_currently_played(self):
        """
        Return ``True`` if song is in state :attr:`.States.playing`
        or :attr:`.States.paused`.
        """
        return self.state in (States.loading, States.playing, States.paused)

    def set_index(self, index):
        """
        Set numeric index for this item.
        """
        self.index = index
        self.update_text()

    def render(self, size, focus=False):
        """
        Render widget & set focused state.
        """
        self.is_focused = focus
        self.update_text()
        return super(SongListItem, self).render(size, focus)


class SongListBoxPopup(urwid.LineBox):
    """
    Widget that represents context popup for a song item.
    """
    signals = ['close']

    def __init__(self, songitem):
        self.songitem = songitem
        self.options = [
            urwid.AttrWrap(
                urwid.Text(' ' + songitem.full_title),
                'panel'
            ),
            urwid.AttrWrap(
                urwid.Text(' Source: {}'.format(songitem.track.source)),
                'panel_divider'
            ),
            urwid.AttrWrap(
                urwid.Text(' StoreID: {}'.format(songitem.track.id)),
                'panel_divider'
            )
        ]

        if not gp.get_track_by_id(songitem.track.id):
            self._add_item('Add to library', self.add_to_my_library)
        else:
            self._add_item('Remove from library', self.remove_from_my_library)

        self._add_item('Create station', self.create_station)

        if self.songitem.track in player.get_queue_tracks():
            self._add_item('Remove from queue', self.remove_from_queue)
        else:
            self._add_item('Append to queue', self.append_to_queue)

        if self.songitem.track.cached_url is not None:
            self._add_item('Copy URL to clipboard', self.copy_url)

        self.options.append(
            urwid.AttrWrap(
                urwid.Button('Close', on_press=self.close),
                'panel',
                'panel_focus'))

        super(SongListBoxPopup, self).__init__(
            urwid.Pile(self.options)
        )

    def _add_item(self, name, func):
        """
        Add an item to the list with a divider.

        Args:
           name (str): The name of the option
           func: The function to call afterwards
        """
        self.options.append(
            urwid.AttrWrap(
                urwid.Divider(u'\u2500'),
                'panel_divider',
                'panel_divider_focus'))

        self.options.append(
            urwid.AttrWrap(
                urwid.Button(name, on_press=func),
                'panel',
                'panel_focus'))

    def add_to_my_library(self, _):
        """
        Add related track to my library.
        """
        def on_add_to_my_library(result, error):
            """
            Show notification with song addition result.
            """
            if error or not result:
                notification_area.notify('Error while adding track to my library: {}'.format(
                    str(error) if error else 'reason is unknown :('
                ))
            else:
                notification_area.notify('Track added to library!')
        self.songitem.track.add_to_my_library_async(callback=on_add_to_my_library)
        self.close()

    def remove_from_my_library(self, _):
        """
        Removes related track to my library.
        """
        def on_remove_from_my_library(result, error):
            """
            Show notification with song removal result.
            """
            if error or not result:
                notification_area.notify('Error while removing track from my library: {}'.format(
                    str(error) if error else 'reason is unknown :('
                ))
            else:
                notification_area.notify('Track removed from library!')
        self.songitem.track.remove_from_my_library_async(callback=on_remove_from_my_library)
        self.close()

    def append_to_queue(self, _):
        """
        Appends related track to queue.
        """
        player.append_to_queue(self.songitem.track)
        self.close()

    def remove_from_queue(self, _):
        """
        Removes related track from queue.
        """
        player.remove_from_queue(self.songitem.track)
        self.close()

    def create_station(self, _):
        """
        Create a station from this track.
        """
        player.create_station_from_track(self.songitem.track)
        self.close()

    def copy_url(self, _):
        """
        Copy URL to clipboard.
        """
        copy(self.songitem.track.cached_url)
        self.close()

    def close(self, *_):
        """
        Close this menu.
        """
        urwid.emit_signal(self, 'close')


class SongListBox(urwid.Frame):
    """
    Displays :class:`.SongListItem` instances.
    """
    signals = ['activate']

    def __init__(self, app, ):
        self.app = app

        self.current_item = None
        self.tracks = []
        self.tracks_walker = urwid.SimpleFocusListWalker([])
        self.walker = urwid.SimpleFocusListWalker([])

        player.track_changed += self.track_changed
        player.media_state_changed += self.media_state_changed

        self.list_box = urwid.ListBox(self.walker)
        self.filter_prefix = '> '
        self.filter_query = ''
        self.filter_box = urwid.Text('')
        self.filter_info = urwid.Text('')
        self.filter_panel = urwid.Columns([
            self.filter_box,
            ('pack', self.filter_info)
        ])
        self.content = urwid.Pile([
            self.list_box,
        ])

        self.overlay = urwid.Overlay(
            top_w=None,
            bottom_w=self.content,
            align='center',
            valign='middle',
            width=50,
            height='pack'
        )

        self.popup = None

        super(SongListBox, self).__init__(
            body=self.content
        )

    def start_filtering(self):
        """
        Starts filtering the song view
        """
        if not hotkey_manager.filtering:
            self.content.contents = [
                (self.list_box, ('weight', 1)),
                (self.filter_panel, ('pack', None))
            ]
            self.app.append_cancel_action(self.end_filtering)
            self.filter_query = ''
            hotkey_manager.filtering = True
            self.tracks_walker[:] = self.walker

            self.filter_box.set_text(self.filter_prefix)

    def perform_filtering(self, char):
        """
        Enter filtering mode (if not entered yet) and filter stuff.
        """
        if char == 'backspace':
            if self.filter_query == "":
                self.end_filtering()
                return
            self.filter_query = self.filter_query[:-1]
        else:
            self.filter_query += char
        self.filter_box.set_text(self.filter_prefix + self.filter_query)

        matches = self.get_filtered_items()
        self.filter_info.set_text('{} matches'.format(len(matches)))
        self.walker[:] = matches
        self.walker.set_focus(0)

        if self.app.current_page.slug == 'library':
            self.update_indexes()

    def get_filtered_items(self):
        """
        Get song items that match the search query.
        """
        matches = []
        for songitem in self.tracks_walker:
            if not isinstance(songitem, SongListItem):
                continue
            if self.filter_query.lower() in songitem.full_title.lower():
                matches.append(songitem)
        return matches

    def end_filtering(self):
        """
        Exit filtering mode.
        """
        if self.filter_box.text == '':
            return
        self.content.contents = [
            (self.list_box, ('weight', 1))
        ]
        hotkey_manager.filtering = False
        self.filter_box.set_text('')
        self.filter_info.set_text('')
        self.walker[:] = self.tracks_walker

    def set_placeholder(self, text):
        """
        Clear list and add one placeholder item.
        """
        self.walker[:] = [urwid.Text(text, align='center')]

    def tracks_to_songlist(self, tracks):
        """
        Convert list of track data items into list of :class:`.SongListItem` instances.
        """
        current_track = player.get_current_track()
        items = []
        current_index = None
        for index, track in enumerate(tracks):
            songitem = SongListItem(track)
            if current_track is not None and current_track == track:
                songitem.set_state(States.loading)
                if current_index is None:
                    current_index = index
            urwid.connect_signal(
                songitem, 'activate', self.item_activated
            )

            urwid.connect_signal(
                songitem, 'play', self.item_play_pause
            )
            urwid.connect_signal(
                songitem, 'append-requested', self.item_append_requested
            )
            urwid.connect_signal(
                songitem, 'unappend-requested', self.item_unappend_requested
            )
            urwid.connect_signal(
                songitem, 'clear-queue', self.clear_queue
            )
            urwid.connect_signal(
                songitem, 'station-requested', self.item_station_requested
            )
            urwid.connect_signal(
                songitem, 'context-menu-requested', self.context_menu_requested
            )
            items.append(songitem)
        return (items, current_index)

    def item_play_pause(self, songitem):
        """
        Called when you want to start playing a song.
        """
        if songitem.is_currently_played:
            player.play_pause()

    def item_activated(self, songitem):
        """
        Called when specific song item is activated.
        Toggles track playback state or loads entire playlist
        that contains current track into player queue.
        """
        page = self.app.current_page
        if songitem.is_currently_played:
            player.play_pause()
        elif page.slug == 'queue':
            player.goto_track(songitem.track)
        # There are some pages like search library where overwriting the queue
        # doesn't make much sense. We can also assume that someone searching
        # for a specific song also wants to append it.
        elif page.append or hotkey_manager.filtering:
            self.item_append_requested(songitem)
        else:
            player.load_queue(self.tracks, songitem.index)

        if hotkey_manager.filtering and page.slug != 'search':
            self.walker[:] = self.get_filtered_items()

    @staticmethod
    def item_append_requested(songitem):
        """
        Called when specific item emits *append-requested* item.
        Appends track to player queue.
        """
        player.append_to_queue(songitem.track)

    @staticmethod
    def item_unappend_requested(songitem):
        """
        Called when specific item emits *remove-requested* item.
        Removes track from player queue.
        """
        player.remove_from_queue(songitem.track)

    @staticmethod
    def item_station_requested(songitem):
        """
        Called when specific item emits *station-requested* item.
        Requests new station creation.
        """
        player.create_station_from_track(songitem.track)

    def context_menu_requested(self, songitem):
        """
        Show context menu.
        """
        self.popup = SongListBoxPopup(songitem)
        self.app.append_cancel_action(self.popup.close)
        self.overlay.top_w = self.popup
        urwid.connect_signal(self.popup, 'close', self.hide_context_menu)
        self.contents['body'] = (self.overlay, None)

    @property
    def is_context_menu_visible(self):
        """
        Return ``True`` if context menu is currently being shown.
        """
        return self.contents['body'][0] is self.overlay

    def hide_context_menu(self):
        """
        Hide context menu.
        """
        if self.popup is not None and self.is_context_menu_visible:
            self.contents['body'] = (self.content, None)
            self.app.unregister_cancel_action(self.popup.close)
            self.popup = None

    def track_changed(self, track):
        """
        Called when new track playback is started.
        Marks corresponding song item (if found in this song list) as currently played.
        """
        for i, songitem in enumerate(self.walker):
            if isinstance(songitem, urwid.Text):
                continue
            if songitem.track == track or \
               (self.app.current_page.slug != 'queue' and songitem.track.id is track.id):
                songitem.set_state(States.loading)
                self.walker.set_focus(i)
            elif songitem.state != States.idle:
                songitem.set_state(States.idle)

    def media_state_changed(self, is_loading, is_playing):
        """
        Called when player media state changes.
        Updates corresponding song item state (if found in this song list).
        """
        current_track = player.get_current_track()
        if current_track is None:
            return

        for songitem in self.walker:
            if isinstance(songitem, urwid.Text):
                continue
            if songitem.track == current_track:
                songitem.set_state(
                    States.loading if is_loading else
                    States.playing if is_playing else
                    States.paused
                )
        self.app.redraw()

    def populate(self, tracks):
        """
        Display a list of :class:`clay.player.Track` instances in this song list.
        """
        self.tracks = tracks
        self.walker[:], current_index = self.tracks_to_songlist(self.tracks)
        self.update_indexes()
        if current_index is not None:
            self.walker.set_focus(current_index)
        elif len(self.walker) >= 1:
            self.walker.set_focus(0)

    def clear_queue(self, _):
        """
        Removes all tracks from the queue
        """
        self.current_item = None
        self.walker.set_focus(0)
        player.clear_queue()

    def append_track(self, track):
        """
        Convert a track into :class:`.SongListItem` instance and appends it into this song list.
        """
        tracks, _ = self.tracks_to_songlist([track])
        self.walker.append(tracks[0])
        self.update_indexes()

    def remove_track(self, track, ):
        """
        Remove a song item that matches *track* from this song list (if found).
        """
        for songlistitem in self.walker:
            if songlistitem.track == track:
                self.walker.remove(songlistitem)

        self.update_indexes()

    def update_indexes(self):
        """
        Update indexes of all song items in this song list.
        """
        for i, songlistitem in enumerate(self.walker):
            songlistitem.set_index(i)

    def keypress(self, size, key):
        return hotkey_manager.keypress("song_view", self, super(SongListBox, self), size, key)

    def mouse_event(self, size, event, button, col, row, focus):
        """
        Handle mouse event.
        """
        if button == 4:
            self.keypress(size, 'up')
        elif button == 5:
            self.keypress(size, 'down')
        else:
            super(SongListBox, self).mouse_event(size, event, button, col, row, focus)
