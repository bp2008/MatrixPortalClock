# This class currently tends to bug out and not render all lines and it spews:
# Warning: Glyph clipped, exceeds descent property: "b" for a bunch of different characters.

import time
from adafruit_display_text import bitmap_label, wrap_text_to_lines

try:
    from typing import Optional
    from fontio import FontProtocol
except ImportError:
    pass


class VerticalScrollingLabel(bitmap_label.Label):
    """VerticalScrollingLabel - A fixed-width, fixed-height line-wrapping label 
    that will scroll text vertically if it exceeds the set number of lines.

    :param font: The font to use for the label.
    :type: ~FontProtocol
    :param int max_characters: The number of characters that sets the fixed-width. Default is 10.
    :param int max_lines: The number of lines that sets the fixed-height. Default is 5.
    :param str text: The full text to show in the label. If this is longer than
     ``max_characters * max_lines`` then the label will scroll to show everything.
    :param float animate_time: The number of seconds in between scrolling animation
     frames. Default is 1 second."""

    # pylint: disable=too-many-arguments
    def __init__(self,
                 font: FontProtocol,
                 max_characters: int = 10,
                 max_lines: int = 5,
                 text: Optional[str] = "",
                 animate_time: Optional[float] = 1,
                 **kwargs) -> None:

        super().__init__(font, line_spacing=1.0, **kwargs)
        self.animate_time = animate_time
        self._current_index = 0
        self._last_animate_time = -1000000
        self.max_characters = max_characters
        self.max_lines = max_lines
        self._lines = []

        self.full_text = text

    def update(self, force: bool = False) -> None:
        """Attempt to update the display. If ``animate_time`` has elapsed since
        previous animation frame then move the lines up by 1 index.
        Must be called in the main loop of user code.

        :param bool force: whether to ignore ``animation_time`` and force the update.
         Default is False.
        :return: None
        """
        _now = time.monotonic_ns() // 1000000
        if force or self._last_animate_time + round(
                self.animate_time * 1000) <= _now:
            print("")
            print("----PRINTING----")
            if len(self._lines) <= self.max_lines:
                _showing_string = "\n".join(self._lines)
                print(_showing_string)
            else:
                self.current_index += 1
                self._last_animate_time = _now

                tmp = []
                for i in range(self.max_lines):
                    print(self._lines[(i + self.current_index) %
                                      len(self._lines)])
                    tmp.append(self._lines[(i + self.current_index) %
                                           len(self._lines)])

                _showing_string = "\n".join(tmp)

            if self.text != _showing_string:
                self.text = _showing_string
        print("----DONE PRINTING----")

    @property
    def current_index(self) -> int:
        """Index of the first visible character.

        :return int: The current index
        """
        return self._current_index

    @current_index.setter
    def current_index(self, new_index: int) -> None:
        if new_index < len(self._lines):
            self._current_index = new_index
        else:
            self._current_index = new_index % len(self._lines)

    @property
    def full_text(self) -> str:
        """The full text to be shown.

        :return str: The full text of this label.
        """
        if len(self._lines) == 0:
            return ""
        return "\n".join(self._lines)

    @full_text.setter
    def full_text(self, new_text: str) -> None:
        if new_text == None:
            new_text = ""
        new_lines = wrap_text_to_lines(new_text, self.max_characters)
        if len(new_lines) > self.max_lines:
            new_lines.append("")
        if (len(new_lines) > 0 and len(self._lines)
                == 0) or ("\n".join(new_lines) != self.full_text):
            self._lines = new_lines
            self._last_animate_time = -1000000
            self.current_index = len(self._lines) - 1
            self.update(True)
