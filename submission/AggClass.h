#ifndef AGGCLASS_H
#define AGGCLASS_H
#include "SingleClass.h"

class AggClass
{
public:
    SingleClass* obj;

    AggClass();
    AggClass(SingleClass* obj_);

};
#endif