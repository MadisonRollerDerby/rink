from django.conf import settings
from django.forms.models import model_to_dict

from selenium.webdriver.chrome import webdriver as web_driver_module
from selenium.common.exceptions import (
    NoSuchElementException, InvalidElementStateException,
    ElementNotVisibleException,
)
from selenium.webdriver.common.keys import Keys


class WebDriver(web_driver_module.WebDriver):

    def key(self, input_name, keys, after_keys=None):
        # Send a keypress of click event to a specific input field name.
        print("K:{} V:{}".format(input_name, keys))

        # If this input is a dropdown, select the option, just click it.
        try:
            self.find_element_by_xpath(
                "//select[@name='{}']/option[@value = '{}']".format(input_name, keys)).click()
            return
        except NoSuchElementException:
            pass

        # Input boxes require a bit more work
        # - click on the input box
        # - enter the text
        # - if necessary, send the after_keys (datepicker needs ESCAPE)
        input = self.find_name(input_name)
        input.click()
        try:
            input.clear()
        except InvalidElementStateException:
            pass  # Checkboxes and selects cannot be cleared.

        input.send_keys(keys)

        if after_keys:
            input.send_keys(after_keys)

    def key_fields(self, key_value_dict={}):
        for key, value in key_value_dict.items():
            self.key(key, value)

    def key_form_fields(self, form):
        # Accepts a django form and fills out the assigned inputs.
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

    def checkbox(self, input_name):
        self.find_element_by_name(input_name).click()

    def find_name(self, input_name):
        elem = self.find_element_by_name(input_name)
        if elem:
            return elem
        raise NoSuchElementException(name)

    def xpath_contains(self, xpath_search, contains):
        # /html/body/div[2]/p[contains(text(),'all done registering')]
        elems = self.find_element_by_xpath("{}".format(
            xpath_search))
        if not elems:
            raise NoSuchElementException(xpath_search)
        if elems.text == contains:
            return True
        return False

    def id_contains(self, id_selector, contains):
        return self.search_contains(id_selector, contains, elem_type="id")

    def class_contains(self, css_selector, contains):
        return self.search_contains(css_selector, contains, elem_type="class")

    def search_contains(self, selector, contains, elem_type):
        # returns the first class that matches the name and text
        # //*[contains(concat(" ", normalize-space(@class), " "), " invalid-feedback ")]
        elems = self.find_element_by_xpath(
            '//*[contains(concat(" ", normalize-space(@{}), " "), " {} ")]'.format(
                elem_type,
                selector,
        ))
        if not elems:
            raise NoSuchElementException(elem_type, selector)
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