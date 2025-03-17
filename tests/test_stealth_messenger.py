import sys
import os
import pytest
import tkinter as tk
from Stealth_Messenger import StealthMessenger
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '../src')))

from stealth_messenger import example_function, another_function

@pytest.fixture
def app():
    """Fixture to initialize the StealthMessenger app."""
    return StealthMessenger()

def test_example_function():
    expected_value = "expected_result_1"  # Replace with the actual expected value
    assert example_function() == expected_value

def test_another_function():
    expected_value = "expected_result_2"  # Replace with the actual expected value
    assert another_function() == expected_value

def test_initial_state(app):
    """Test the initial state of the app."""
    assert app.message_window is None
    assert app.bg_color == 'white'
    assert app.fg_color == 'black'
    assert app.msg_x == 250
    assert app.msg_y == 250
    assert app.font_size == 14
    assert app.alpha_value == 0.05

def test_display_message(app):
    """Test the display_message method."""
    root = tk.Tk()
    app.message_window = None
    app.alpha_value = 0.5
    app.bg_color = 'white'
    app.fg_color = 'black'
    app.msg_x = 100
    app.msg_y = 100
    app.font_size = 12

    # Call the method
    from Stealth_Messenger import display_message
    display_message("Test Message")

    # Assertions
    assert app.message_window is not None
    assert app.message_window.attributes('-alpha') == 0.5
    assert app.message_window.cget('bg') == 'white'

    # Cleanup
    app.message_window.destroy()
    root.destroy()

def test_set_mode(app):
    """Test the set_mode method."""
    from stealth_messenger import set_mode
    set_mode('dark')
    assert app.bg_color == 'black'
    assert app.fg_color == 'white'

    set_mode('light')
    assert app.bg_color == 'white'
    assert app.fg_color == 'black'

def test_change_font_size(app):
    """Test the change_font_size method."""
    from Stealth_Messenger import change_font_size
    change_font_size(2)
    assert app.font_size == 16

    change_font_size(-10)
    assert app.font_size == 6  # Minimum font size

    change_font_size(100)
    assert app.font_size == 72  # Maximum font size

def test_change_transparency(app):
    """Test the change_transparency method."""
    from Stealth_Messenger import change_transparency
    change_transparency(0.1)
    assert app.alpha_value == 0.15

    change_transparency(-0.2)
    assert app.alpha_value == 0.05  # Minimum transparency

    change_transparency(1.0)
    assert app.alpha_value == 1.0  # Maximum transparency