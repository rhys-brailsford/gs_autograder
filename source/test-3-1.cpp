#include <iostream>
#include "SingleClass.h"
using namespace std;

int main()
{
    SingleClass obj1(5);
    cout << obj1.getX() << endl;

    SingleClass obj2(10);
    cout << obj2.getX() << endl;
}