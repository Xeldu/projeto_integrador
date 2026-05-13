import sys, os
sys.path.insert(0, os.path.join(os.path.dirname(__file__), ".."))
from test_page import render_test_page
render_test_page("temperature", "°C")
