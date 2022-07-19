# CMacro

Execute any C source code in your Python script.

## Usage

```py
import cmacro

cmacro.macro("""
#include <stdio.h>

int main(int argc, char **argv)
{
    printf("Hello World!\\n");
}
""")
```

Voilà! You printed "Hello World!" using C in your Python script.

\[More docs coming soon!\]

