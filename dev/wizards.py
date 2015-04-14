template_main_cpp = r'''/**
 * Print a simple "Hello world!"
 *
 * @file main.cpp
 * @section LICENSE

    This code is under MIT License, http://opensource.org/licenses/MIT
 */

#include <iostream>

int main() {
  std::cout << "Hello world!\n";
}
'''

template_main_c = r'''/**
 * Print a simple "Hello world!"
 *
 * @file main.c
 * @section LICENSE

    This code is under MIT License, http://opensource.org/licenses/MIT
 */

#include <stdio.h>

int main(void)
{
  printf("Hello World!");
}
'''

template_main_arduino = r'''/**
 * It blinks an LED. In this case, LED in pin 13 with a time delay of 1 second
 *
 * @file main.cpp
 * @section LICENSE

    This code is under MIT License, http://opensource.org/licenses/MIT
 */


#include "Arduino.h"

// Pin 13 has an LED connected on most Arduino boards.
int led = 13;

// the setup routine runs once when you press reset:
void setup() {
    pinMode(led, OUTPUT);     // initialize the digital pin as an output.
}

// the loop routine runs over and over again forever:
void loop() {
    digitalWrite(led, HIGH);   // turn the LED on (HIGH is the voltage level)
    delay(1000);               // wait for a second
    digitalWrite(led, LOW);    // turn the LED off by making the voltage LOW
    delay(1000);               // wait for a second
}
'''

template_main_fortran90 = '''program HelloWorld
  write (*,*) 'Hello world!'
end program HelloWorld
'''

template_main_nodejs = '''var sys = require("sys");
sys.puts("Hello world!");
'''

template_main_python = '''def main():
    print "Hello world!"

if __name__ == "__main__":
    main()
'''

mains_templates = {'cpp': ['main.cpp', template_main_cpp],
                   'c': ['main.c', template_main_c],
                   'arduino': ['main.cpp', template_main_arduino],
                   'fortran': ['main.f90', template_main_fortran90],
                   'node': ['main.js', template_main_nodejs],
                   'python': ['main.py', template_main_python]}


def get_main_file_template(language='cpp'):
        ''' Return, if exists, the template file for the specified language '''
        if mains_templates.get(language):
            file_name, content = mains_templates[language]
            return file_name, content
        else:
            from biicode.client.exception import ClientException
            raise ClientException("Bad language introduced (%s)! "
                                  "It should be one of %s" % (language,
                                                              mains_templates.keys()))
