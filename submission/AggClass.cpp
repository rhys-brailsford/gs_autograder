#include "AggClass.h"

AggClass::AggClass()
{
    obj = new SingleClass();
}

AggClass::AggClass(SingleClass* obj_)
{
    obj = obj_;
}