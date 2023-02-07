"""
Flask web site with vocabulary matching game
(identify vocabulary words that can be made
from a scrambled string)
"""

import flask
import logging
from flask import request

# Our modules
from src.letterbag import LetterBag
from src.vocab import Vocab
from src.jumble import jumbled
import src.config as config


###
# Globals
###
app = flask.Flask(__name__)

CONFIG = config.configuration()
app.secret_key = CONFIG.SECRET_KEY  # Should allow using session variables

#
# One shared 'Vocab' object, read-only after initialization,
# shared by all threads and instances.  Otherwise we would have to
# store it in the browser and transmit it on each request/response cycle,
# or else read it from the file on each request/responce cycle,
# neither of which would be suitable for responding keystroke by keystroke.

WORDS = Vocab(CONFIG.VOCAB)
SEED = CONFIG.SEED
try:
    SEED = int(SEED)
except ValueError:
    SEED = None


###
# Pages
###

@app.route("/")
@app.route("/index")
def index():
    """The main page of the application"""
    flask.g.vocab = WORDS.as_list()
    flask.session["target_count"] = min(
        len(flask.g.vocab), CONFIG.SUCCESS_AT_COUNT)
    flask.session["jumble"] = jumbled(
        flask.g.vocab, flask.session["target_count"], seed=None if not SEED or SEED < 0 else SEED)
    flask.session["matches"] = []
    app.logger.debug("Session variables have been set")
    assert flask.session["matches"] == []
    assert flask.session["target_count"] > 0
    app.logger.debug("At least one seems to be set correctly")
    return flask.render_template('vocab.html')


#app.route("/keep_going") no longer needed


@app.route("/completed")
def success():
    return flask.render_template('success.html')


#######################
# Form handler.
#   You'll need to change this to a
#   a JSON request handler
#######################

@app.route("/_check")
def check():
    """
    User has submitted the form with a word ('attempt')
    that should be formed from the jumble and on the
    vocabulary list. We respond depending on whether
    the word is on the vocab list (therefore correctly spelled),
    made only from the jumble letters, and not a word they
    already found.
    """
    app.logger.debug("Entering check")

    # The data we need, from form and from cookie
    text = request.args.get("text", type=str) # Get the text from the form arguments
    jumble = flask.session["jumble"] # Get the jumble from the session
    matches = flask.session.get("matches", [])  # Default to empty list, get the matches from the session

    # Is it good?
    in_jumble = LetterBag(jumble).contains(text) # Check if text can be made from the letters in jumble
    matched = WORDS.has(text) # Check if text is in the list of words


    # Respond appropriately
    """ Most of this checking logic is from minijax.py"""
    if matched and in_jumble and not (text in matches):
        # Check if text is a new word
        matches.append(text) # Add the new word to the list of matches
        flask.session["matches"] = matches # Save the updated list of matches in the session
        sval = {"success_count": CONFIG.SUCCESS_AT_COUNT} # Set the success count using the value from the CONFIG
        outcome = {"valid_word": True} # Set the outcome as True, indicating that the text is a valid word
        return flask.jsonify(result=outcome, success=sval)
    elif text in matches:
        # Check if text is already in the list of matches
        sval = {"success_count": CONFIG.SUCCESS_AT_COUNT} # Set the success count using the value from the CONFIG
        outcome = {"valid_word": False} # Set the outcome as False, indicating that the text is not a new word
        return flask.jsonify(result=outcome, success=sval)
    elif not matched:
        # Check if text is in the list of words
        sval = {"success_count": CONFIG.SUCCESS_AT_COUNT} # Set the success count using the value from the CONFIG
        outcome = {"valid_word": False} # Set the outcome as False, indicating that the text is not in the list of words
        return flask.jsonify(result=outcome, success=sval)
    elif not in_jumble:
        # Check if text can be made from the letters in jumble
        sval = {"success_count": CONFIG.SUCCESS_AT_COUNT} # Set the success count using the value from the CONFIG
        outcome = {"valid_word": False} # Set the outcome as False, indicating that the text can't be made from the letters in jumble
        return flask.jsonify(result=outcome, success=sval)
    else:
        app.logger.debug("This case shouldn't happen!") # Debug statement in case the execution reaches this point
        assert False  # Raise an AssertionError

    """This was unecessary to have at this point because the change it input reading"""
    # Choose page: Solved enough, or keep going?
    # if len(matches) >= flask.session["target_count"]:
    #    return flask.redirect(flask.url_for("success"))
    # else:
    #    return flask.redirect(flask.url_for("keep_going"))
    # Dont need this, because dynamically refreshed by keystroke



###############
# AJAX request handlers
#   These return JSON, rather than rendering pages.
###############

@app.route("/_example")
def example():
    """
    Example ajax request handler
    """
    app.logger.debug("Got a JSON request")
    rslt = {"key": "value"}
    return flask.jsonify(result=rslt)


#################
# Functions used within the templates
#################

@app.template_filter('filt')
def format_filt(something):
    """
    Example of a filter that can be used within
    the Jinja2 code
    """
    return "Not what you asked for"

###################
#   Error handlers
###################


@app.errorhandler(404)
def error_404(e):
    app.logger.warning("++ 404 error: {}".format(e))
    return flask.render_template('404.html'), 404


@app.errorhandler(500)
def error_500(e):
    app.logger.warning("++ 500 error: {}".format(e))
    assert not True  # I want to invoke the debugger
    return flask.render_template('500.html'), 500


@app.errorhandler(403)
def error_403(e):
    app.logger.warning("++ 403 error: {}".format(e))
    return flask.render_template('403.html'), 403


#############

if __name__ == "__main__":
    if CONFIG.DEBUG:
        app.debug = True
        app.logger.setLevel(logging.DEBUG)
        app.logger.info(
            "Opening for global access on port {}".format(CONFIG.PORT))
    app.run(port=CONFIG.PORT, host="0.0.0.0", debug=CONFIG.DEBUG)