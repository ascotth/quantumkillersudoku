# quantumkillersudoku
Exploration of using adiabatic quantum computing to solve Killer Sudoku.

## Introduction
D-Wave Systems (https://www.dwavesys.com/) include among their various examples, the use of a Binary Quadratic Model (BQM) to solve typical Sudoku problems (https://github.com/dwave-examples/sudoku).

Here, we explore a similar approach to the solution of Killer Sudoku puzzles.

The specific difference between standard Sudoku and Killer Sudoku is that, while the standard form provides values for certain cells in the problem board, the Killer variant divides the board into "cages" each of which contains several cells and a target value to which the cell contents must sum.

This difference has implications for the types of constraint that appear in the associated BQM: constraints for the standard Sudoku include ones which map values to cells, where such are known, whereas the Killer variant must include constraints appropriate to the possible contents of cages.

In order to limit the complexity of the problem, only Killer boards with cages of size 2 or 3 cells are considered. 

## Usage
To use your own Killer Sudoku board:

python killer.py board.txt

or to use a default samples:

python killer.py 9

for the sampel 9 x 9 puzzle

or 

python killer.py 4

for the sample 4 x 4 puzzle.