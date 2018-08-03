from django.conf import settings
from django.forms.models import model_to_dict

from selenium.webdriver.chrome import webdriver as web_driver_module
from selenium.common.exceptions import (
    NoSuchElementException, InvalidElementStateException,
    ElementNotVisibleException,
)
from selenium.webdriver.common.keys import Keys


class WebDriver(web_driver_module.WebDriver):
    """Our own WebDriver with some helpers added"""

    def key(self, input_name, keys, after_keys=None):
        input = self.find_name(input_name)
        input.click()
        try:
            input.clear()
        except InvalidElementStateException:
            pass

        #  print("K:{} V:{}".format(input_name, keys))
        input.send_keys(keys)
        
        if after_keys:
            #  Sometimes we need to send a little bit of ESCAPE keys or etc.
            #  to close a window or something.
            input.send_keys(after_keys)

    def key_fields(self, key_value_dict={}):
        for key, value in key_value_dict.items():
            self.key(key, value)

    def key_form_fields(self, form):
        for field in form.fields:
            if field not in ['id', ]:
                value = form[field].value()
                after_keys = None

                # Properly format dates in these inputs
                # For some reason selenium and django don't place nice here.
                if form[field].value().__class__.__name__ == "date":
                    value = value.strftime(settings.DATE_FORMAT_PYTHON)
                    after_keys = Keys.ESCAPE

                try:
                    self.key(field, str(value), after_keys=after_keys)
                except KeyError:
                    pass
                except NoSuchElementException:
                    pass  # we are lazy and just want the forms filled.
                except ElementNotVisibleException:
                    pass

    def find_name(self, input_name):
        elem = self.find_element_by_name(input_name)
        if elem:
            return elem
        raise NoSuchElementException(name)

    def class_contains(self, css_selector, contains):
        # returns the first class that matches the class name and text
        # //*[contains(concat(" ", normalize-space(@class), " "), " invalid-feedback ")]
        elems = self.find_element_by_xpath('//*[contains(concat(" ", normalize-space(@class), " "), " {} ")]'.format(css_selector))
        if not elems:
            raise NoSuchElementException(css_selector)
        if elems.text == contains:
            return True
        return False

    def find_css(self, css_selector):
        """Shortcut to find elements by CSS. Returns either a list or singleton"""
        elems = self.find_elements_by_css_selector(css_selector)
        found = len(elems)
        if found == 1:
            return elems[0]
        elif not elems:
            raise NoSuchElementException(css_selector)
        return elems

    def wait_for_css(self, css_selector, timeout=7):
        """ Shortcut for WebDriverWait"""
        return WebDriverWait(self, timeout).until(lambda driver : driver.find_css(css_selector))