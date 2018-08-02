from selenium.webdriver.chrome import webdriver as web_driver_module
from selenium.common.exceptions import NoSuchElementException


class WebDriver(web_driver_module.WebDriver):
    """Our own WebDriver with some helpers added"""

    def key(self, input_name, keys):
        input = self.find_name(input_name)
        input.click()
        input.clear()
        input.send_keys(keys)

    def key_fields(self, key_value_dict={}):
        for key, value in key_value_dict.items():
            self.key(key, value)

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