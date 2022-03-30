#include <iostream>
using namespace std;

extern int multiply(int a, int b);

int main(int argc, char** argv)
{
    int test = 0;
    if (argc > 1)
    {
        test = atoi(argv[1]);
    }

    if (test == 0)
    {
        cout << multiply(2, 3) << endl;
    }
    else if (test == 1)
    {
        cout << multiply(9, -2) << endl;
    }
}