#include "port_bridge.h"
#include <string.h>

/* Intercept diagnostics before libntr initializes graphics or requests a ROM.
   Ordinary launches are forwarded to the original SDK entry point. */
int __real_main(int argc, char **argv);
int __wrap_main(int argc, char **argv)
{
    if (argc == 2 && !strcmp(argv[1], "--universe-self-test"))
        return Universe_PortSelfTest();
    return __real_main(argc, argv);
}
