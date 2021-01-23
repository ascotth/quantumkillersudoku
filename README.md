# quantumkillersudoku
Exploration of using adiabatic quantum computing to solve Killer Sudoku.

## Introduction
D-Wave Systems (https://www.dwavesys.com/) include among their various examples, the use of a Binary Quadratic Model (BQM) to solve typical Sudoku problems (https://github.com/dwave-examples/sudoku).

Here, we explore a similar approach to the solution of Killer Sudoku puzzles.

The specific difference between standard Sudoku and Killer Sudoku is that, while the standard form provides values for certain cells in the problem board, the Killer variant divides the board into "cages" each of which contains several cells and a target value to which the cell contents must sum.

This difference has implications for the types of constraint that appear in the associated BQM: constraints for the standard Sudoku include ones which map values to cells, where such are known, whereas the Killer variant must include constraints appropriate to the possible contents of cages.

In order to limit the complexity of the problem, only Killer boards with cages of size 2 or 3 cells are considered. 

## Usage
To use your own Killer Sudoku puzzle (called board.txt here):

python killer.py board.txt

or to use a default samples:

python killer.py 9

for the sampel 9 x 9 puzzle

or 

python killer.py 4

for the sample 4 x 4 puzzle.

## Input file format
For this exercise, cages are restricted to have either 2 or 3 cells, each cell being described by its row and column.

The rows and columns of a 9 x 9 puzzle are numbered 0 - 8, so the top left cell is 0,0 and the bottom right, 8,8.

Each line of the input file describes a single cage in the following form (showing a cage of size 2 and then  
one of size 3):

r1,c1 r2,c2 t  
r3,c3 r4,c4 r5,c5 u  

where r1,c1 - r5,c5 are the coordinates of the cells in row,column form and t,u are the respective cage totals. All entries
on a line are space separated.

To make this more explicit, here is the contents of the easy_4.txt sample file:

0,0 0,1 1,0 6  
0,2 1,1 1,2 8  
0,3 1,3 2,3 7  
2,0 2,1 5  
2,2 3,2 3,3 9  
3,0 3,1 5  

In this sample, the lines 1 - 3 and 5 describe cages having 3 cells each and summing to 6, 8, 7 and 9 respectively,  and lines 4 and 6 describe 
cages containing 2 cells each, each summing to 5. The 16 cells of the 4 x 4 board are included in one and only one line (as cages do not overlap, 
and all cells are included in a cage).

It's worth noting that this quite simple puzzle has 3 linear cages on lines 3, 4 and 6, with L shaped cages on lines 1, 2 and 5.


## A Note on Solutions
The proposed solution is checked for the usual constraints: that each digit appears once and only once in each row, column 
and subsquare.

Cage totals are also checked.

However, it may be that a puzzle has multiple possible solutions, each satisfying these constraints, so a correct solution may not exactly match the original board used to create the puzzle.
