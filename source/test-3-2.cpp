#include <iostream>
#include "AggClass.h"
using namespace std;

int main()
{
    SingleClass* obj1 = new SingleClass(8);

    AggClass agg(obj1);
    cout << agg.obj->getX() << endl;

    delete obj1;
}