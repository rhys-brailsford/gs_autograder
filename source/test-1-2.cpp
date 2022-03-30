#include <iostream>
using namespace std;

extern int maximum(int* arr, int n);

int main(int argc, char** argv)
{
    int test = 0;
    if (argc > 1)
    {
        test = atoi(argv[1]);
    }

    int testArr[] = {5,2,8,3, 1,15,9,10};

    if (test == 0)
    {
        cout << maximum(testArr, 4) << endl;
    }
    else if (test == 1)
    {
        cout << maximum(testArr, 8) << endl;
    }
    else if (test == 2)
    {
        cout << maximum(testArr, 2) << endl;
    }
}