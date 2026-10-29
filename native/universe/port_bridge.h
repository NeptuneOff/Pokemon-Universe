#ifndef UNIVERSE_PORT_BRIDGE_H
#define UNIVERSE_PORT_BRIDGE_H
/* Private hooks used only in the downstream PC source build. */
void Universe_PortStartup(void);
void Universe_BattleBegin(const void *context);
void Universe_BattleEnd(const void *context);
int Universe_PortSelfTest(void);
#endif
