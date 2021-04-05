import math
import sys
from itertools import permutations  
from collections import namedtuple

import dimod

from hybrid.reference import KerberosSampler
from dimod.generators.constraints import combinations

# A Cell represents a board location with coordinates r and c 
Cell = namedtuple('Cell', ['r', 'c']) 

# The Cells and target value of a cage
Inputcage = namedtuple('Inputcage', ['cells', 'target']) 

# Collects all relevant information about a cage, including possible patterns
Cage = namedtuple('Cage', ['size','cells', 'target','layout','singles','multis','corner'])


def addon(lists, togo, target, size):
    """Extends each of the lists by a single integer, with the aim of creating 
    lists whose members sum to the target value.
    
    Each list contains non-decreasing elements, so the added number must be at 
    least as large as the final element of the input list.
    The size value determines the largest value that may be added to a list, 
    and the togo value indicates how many more elements will be added to the 
    input lists.
    
    Args:
        lists (list): contains elements which are lists of integers in the 
                      range 1 - 9. All members are of equal length.
        togo (int): how many more elements will be added after this.
        target (int): the number to which the elements of each list 
                      will sum when completed.
        size (int): the largest integer allowed in a list.
        
    Returns:
        (list): the list of lists.
    """
    return [s + [i] for s in lists for i in range(s[-1],size+1) if (sum(s) + (togo + 1)*i) <= target if (i + sum(s) + togo*size) >= target]
    
def allseq(length, target, size):
    """Creates a list containing lists of integers in the 
    range 1 - size adding to the target value.
    
    Each list contains a collection of integers that could be used 
    to populate a Killer Sudoku cage whose total value is target.
    As such, lists whose elements are all equal are filtered out.
    
    Lists of the form [a b b] or [a a b] are allowed as they
    could populate an angled cage spanning two or three subsquares
    with the equal elements in different subsquares with the single
    value in the corner position.
    
    Args:
        length (int): the length of the required lists.
        target (int): the value to which the list elements must sum.
        size (int): the largest integer allowed in a list.
        
    Returns:
        (list): the list of lists of integers.
     """
    lists = [[i] for i in range(1,size+1)]
    
    for togo in range(length - 1, 0, -1):
        lists = addon(lists, togo-1, target, size)
    
    # reject ones which are all the same as that would violate row/column rule
    lists = [p for p in lists if min(p) < max(p)]
    return lists

def generate_patterns(size):
    """
    Generate patterns for cages with 2 or 3 cells.
    
    Three types of pattern are created:
       "short" patterns for cages with 2 cells
       "single" patterns suitable for 3 cell cages where
        the cage is linear or angled within the same subsquare
       "multi" suitable for angled caged which span 2 or 3 subsquares, 
        so may contain 2 numbers which are the same.
        
    Args:
        size (int): the maximum value allowed for a number.
                    In practice: 4 or 9 to be used in Sudoku
                    puzzles of dimensions 4 x 4 or 9 x 9.
                    
    Returns:
        dict(str: dict): a dictioanry containing three
                   dictionaries, one for each of the types
                   'short', 'single' and 'multi'
                   Each value is a dictionary whose keys
                   are integer targets and whose values are
                   the patterns summing to that target.                   
    """
    patterns = {'short':{},'single':{},'multi':{}}
    for target in range(3,2*size):
        patterns['short'][target] = allseq(2,target, size)
        
    for target in range(4, 3*size):
        p = allseq(3,target,size)
        p_single = [s for s in p if s[0] < s[1] < s[2]]
        p_multi = [s for s in p if not s in p_single]
        
        patterns['multi'][target] = p_multi
        if len(p_single) > 0:
            patterns['single'][target] = p_single
        
    return patterns

def span(cells):
    """Produces information regarding the layout of a group of cells.
    
    For each cell in cells, record the location (row and column) of the cell.
    
    Also record a row or column common to two or more cells.
    
    Args:
        cells (list): a list of type Cell.
        
    Returns:
        (tuple): the rows and columns containing one of the cells,
                 and the row and/or column shared by several cells.
    """
    rows = []
    cols = []
    
    shared_r = -1
    shared_c = -1
    for cell in cells:
        if cell.r in rows:
            shared_r = cell.r
        else:
            rows.append(cell.r)
            
        if cell.c in cols:
            shared_c = cell.c
        else:
            cols.append(cell.c)          

    return rows, cols, shared_r, shared_c

def classify(cells, side):
    """Classifies collections of 2 or 3 cells.
    
    The three classifications are:
       'straight' - all cells lie in a single row of column
       'angle'    - 3 cells in an L shape but lying within a single subsquare
       'span'     - 3 cells in an L shape spanning two or three subsquares.
       
    Args:
        cells (list): a list of 2 or 3 Cells
        side (int): the size of a subsquare (2 or 3 for a 4 x 4 or 9 x 9 board)
        
    Returns:
        (tuple): the category (str) and the corner Cell for a span (or None)
    """
    rows, cols, shared_r, shared_c = span(cells)
    
    if len(rows) == 1 or len(cols) == 1:
        return 'straight',None

    rows_mod = {r//side for r in rows}
    cols_mod = {c//side for c in cols}
    
    if len(rows_mod)+len(cols_mod) == 2:
        return 'angle',None
    
    return 'span',Cell(shared_r,shared_c)
    
def create_perms():
    """Creates a dictionary of permutations.
    
    Permutations of the numbers 0,1 or 0,1,2 for use in
    indexing permutations of cell targets.
    """
    perms = {}
    numbers = [i-1 for i in range(1,3)]
    perms[2] = [i for i in permutations(numbers)]          
    numbers = [i-1 for i in range(1,4)]
    perms[3] = [i for i in permutations(numbers)]          

    return perms

def generate_variable(r, c, n):
    """Creates a label for the coordinates and contents of a cell."""
    return f'{r},{c}_{n}'

def allocate_numbers(cage, perms):
    """Creates all allowed arrangements of values for a cage.
    
    Each cage has a target value, a collection of Cells and a collection
    of patterns of integers each of which sums to the target. 
    
    Each collection of values, e.g. [1,3,4] for a target of 8,
    can be allocated to the cells in different ways, and the 
    permutations are used to perform this by permuting the indexes
    of the values.
    
    Example: cage with coordinates [0,1 0,2 1,2] and target of 8
    generates the following, using labels of the for a,b_c to
    denote locating the value c to the cell in row a and column b:
    [('0,1_1','0,2_3','1,2_4'), ('0,1_1','0,2_4','1,2_3'),
     ('0,1_3','0,2_4','1,2_1'), ('0,1_3','0,2_1','1,2_4'),
     ('0,1_4','0,2_1','1,2_3'), ('0,1_4','0,2_3','1,2_1')]
    
    Args:
        cage (Cage): the cage used to generate values
        perms (dict): the permutations used to create variants of the
                      allowed values for the cage.
                      
    Returns:
        (list): a list of all allowed possible allocations of
                values to cells in the cage.
    """
    values = []
    
    cells = cage.cells
    
    size = cage.size
    for pattern in cage.singles:
        for p in perms[size]:
            cellvals = []
            ind = 0
            for cell in cells:
                cellvals.append(generate_variable(cell.r, cell.c,pattern[p[ind]]))
                ind += 1
            values.append(tuple(cellvals))
            
    if cage.layout == 'span':
        for pattern in cage.multis:
            if pattern[0] == pattern[1]:
                corner_val = pattern[2]
                dup_val = pattern[0]
            else:
                corner_val = pattern[0]
                dup_val = pattern[2]
                
            cellvals = []
            ind = 0
            for cell in cells:
                if cell == cage.corner:
                    cellvals.append(generate_variable(cell.r, cell.c, corner_val))
                else:
                    cellvals.append(generate_variable(cell.r, cell.c, dup_val))                    
                ind += 1
            values.append(tuple(cellvals))

    return values
	
def merge_tuple(tup1, tup2):
    t1 = [i for i in tup1]
    t2 = [i for i in tup2]
    return tuple(t1 + t2)
    
def add_to_poly(poly, values):
    """Adds items to the polynomial from the values associated with a cage.
    
    The polynomial has terms as keys and coefficients as values.
    
    For a cage with 3 cells, the values are tuples of the form (a,b,c) where
    each element is the association of a value to a cell (e.g. 2,4_7 denoting
    the cell on row 2 and column 4 contains the number 7).
    
    The terms created are of three types:
        singletons (e.g. a, b, c)
        cubics (e.g. abc)
        and sextics (e.g. abcdef)
        
    For example, if the values contain the tuples (a,b,c) and (d,e,f) the items 
    added to the polynomial are of the form:
    
    (a):1, (b):1, (c):1, (d):1, (e):1, (f): 1,
    (abc): -10, (def): -10
    (abcdef): 15
    
    As a polynomial this is: 
    a + b + c + d + e + f -10abc -10def +15abcdef
    
    For a linear cage of size 3, there are 6 such tuples, resulting in
    the addition of 18 singeltons, 6 cubics and 15 sextics.
    
    Args:
        poly (dict): the polynomial being populated.
        values (list): a list of tuples representing the possible
                       allocations to the cells of a cage.
    """
    for v in values:
        for cv in v:
            tv = [cv]
            poly[tuple(tv)] = 1
        
        poly[v] = -10
        
    lv = len(values)
    
    for i in range(lv-1):
        for j in range(i+1,lv):
            poly[merge_tuple(values[i], values[j])] = 15
        
def cell_from_coords(text):
    coords = text.split(',')
    if len(coords) == 2:
        return Cell(int(coords[0]),int(coords[1]))
    else:
        print(f'Bad coords {text}')

def parse_line(line):
    """Returns an Inputcage containing the cells whose coordinates
    appear on the line. Final entry is the target for that cage.
    
    Note: Puzzles supported by this script contain only cages with 2 or 3 cell .

    Args:
        line (str): represents a cage in the form
                    a,b c,d t   or
                    a,b c,d e,f t
                    where a - f are the row and column coordinates of 
                    the cells in the cage and t is the target value.
    Returns:
        (Inputcage): containing the Cells and target for the cage
                    
                        
    """
    line = line.rstrip()
    parts = line.split(' ')

    cells = [cell_from_coords(p) for p in parts[:len(parts) - 1]]
    target = int(parts[-1])
    return Inputcage(cells, target)
    

def read_puzzle(path):
    """Returns a list of lists containing the contents of the input text file.

    """
    with open(path, "r") as f:
        content = f.readlines()

    cages = [] 
    size = 0
    
    for line in content:
        print(line)
        inputcage = parse_line(line)
        size += len(inputcage.cells)
        cages.append(inputcage)
        
    print(f'\nPuzzle has {size} cells.\n\n')
    
    return cages, size
           
def make_cage(incage, patterns, side):
    """Creates a Cage using the input data, patterns and size of a subsquare.
    
    Args:
        incage (Inputcage): the Cells and target value for the cage
        patterns (dict): dictionary of dictionaries. Outer key: cell shape;
                         inner key: target values 
        side (int): the subsquare side length (E.g. 3 for a 9 x 9 puzzle).
        
    Returns:
        (Cage): fully specified cage, including patterns of cell values,
                and corner, if an angled cage spanning subsquares.
            
    """
    cells = incage.cells
    target = incage.target

    multis = []
    corner=None
    if len(cells) == 2:
        layout = 'short'
        singles = patterns['short'][target]
        size = 2
    else:
        size = 3
        layout, corner = classify(cells, side)
        if layout in ['straight','angle']:
            singles = patterns['single'][target]
        else:
            singles = patterns['single'][target]
            multis = patterns['multi'][target]
            
    return Cage(size, cells, target, layout, singles, multis, corner)

def make_board(incages, patterns, side):
    """Creates a collection of Cages from the input data.
    
     Args:
        incages (list): the Inputcages assembled from input data
        patterns (dict): dictionary of dictionaries. Outer key: cell shape;
                         inner key: target values 
        side (int): the subsquare side length (E.g. 3 for a 9 x 9 puzzle).
        
    Returns:
        (list): of Cages representing the puzzle.
        
    """
    board = []
    for incage in incages:
        board.append(make_cage(incage, patterns, side))
        
    return board

def add_basic_constraints(poly, size):
    """Creates a Binary Quadratic Model representing the problem to be solved.
    
    The polynomial has singleton, cubic and sextic entries; in particular, 
    it has order 6.
    
    A Binary Quadratic Model is created from the polynomial, and then
    the usual constraints are added, specifying that each cell contains
    precisely one digit chosen from the range 1 - size,
    that each row and column of cells contains the digits 1 - size 
    precisely once, and that each subsquare also contains these digits
    once.
    
    Args:
        poly (dict): the polynomial, keyed on the variables with values the 
                     associated coefficients.
        size (int): the size of the board (e.g. 9 for a 9 x 9 puzzle)
        
    Returns:
        (BinaryQuadraticModel): the model containing the standard sudoku
              constraints plus those necessary to constrain each cage to 
              values which sum to the cage target.
    """
    bqm = dimod.make_quadratic(poly, 10.0, dimod.BINARY)
    digits = range(1, size+1)
    # Constraint: Each node can only select one digit
    for row in range(size):
        for col in range(size):
            node_digits = [generate_variable(row, col, digit) for digit in digits]
            one_digit_bqm = combinations(node_digits, 1)
            bqm.update(one_digit_bqm)

    # Constraint: Each row of nodes cannot have duplicate digits
    for row in range(size):
        for digit in digits:
            row_nodes = [generate_variable(row, col, digit) for col in range(size)]
            row_bqm = combinations(row_nodes, 1)
            bqm.update(row_bqm)

    # Constraint: Each column of nodes cannot have duplicate digits
    for col in range(size):
        for digit in digits:
            col_nodes = [generate_variable(row, col, digit) for row in range(size)]
            col_bqm = combinations(col_nodes, 1)
            bqm.update(col_bqm)
            
    # Constraint: Each subsquare must contain all of the digits once
    for r in range(size):
        for c in range(size):
            for digit in digits:
                # Shifts for moving subsquare inside sudoku matrix
                row_shift = r * size
                col_shift = c * size

                # Build the labels for a subsquare
                subsquare = [get_label(row + row_shift, col + col_shift, digit)
                             for row, col in subsquare_indices]
                subsquare_bqm = combinations(subsquare, 1)
                bqm.update(subsquare_bqm)

    return bqm

def cell_desc(cell):
    return str(cell.r) + ',' + str(cell.c)

def cage_desc(cage):
    coords = [cell_desc(cell) for cell in cage.cells]
    cell_str = ' '.join(coords)
    return f'Cells {cell_str} should sum to {cage.target}'

def check_cage(cage, board):
    """Compares the cage target with the sum of the cells.
    
    Using the board values, compute the sum of the cage's cells
    and compare with the required target value, returning a
    boolean to indicate success or not and a message
    describing the failure if any.

    Args:
        cage(Inputcage): the cells and target for a specific cage
        board(list): a list of lists containing the cells values

    Returns:
        (bool): True if success, False otherwise
        (str/None): if failure, a brief explanation of the failed sum
    """
    total = 0
    for cell in cage.cells:
        total += board[cell.r][cell.c]
    message = None
    ok = (total == cage.target)

    if not ok:
        desc = cage_desc(cage)
        message = f'{desc} but actual total is {total}'
    return ok, message
    
def check_solution(board, cages):
    """Verify that the board satisfies the Sudoku constraints.

    Args:
      board(list of lists): list contains 'n' lists, where each of the 'n'
        lists contains 'n' digits. 
      cages(list): the list of Inputcages used to capture the puzzle.
    """
    n = len(board)        # Number of rows/columns
    m = int(math.sqrt(n))  # Number of subsquare rows/columns
    unique_digits = set(range(1, n+1))  # Digits in a solution
  
    # check rows
    row_probs = []
    for row in board:
        if set(row) != unique_digits:
            row_probs.append(row)

    # check columns
    col_probs = []
    for j in range(n):
        col = [board[i][j] for i in range(n)]
        if set(col) != unique_digits:
            col_probs.append(col)

    # check subsquares
    sub_probs = []
    subsquare_coords = [(i, j) for i in range(m) for j in range(m)]
    for r in range(m):
        for c in range(m):
            subsquare = [board[i + r * m][j + c * m] for i, j
                         in subsquare_coords]
            if set(subsquare) != unique_digits:
                sub_probs.append(subsquare)
    cage_probs = []
    for cage in cages:
        ok, message = check_cage(cage, board)
        if not ok:
            cage_probs.append(message)
            
    if len(row_probs) + len(col_probs) + len(sub_probs) + len(cage_probs) == 0:
        print("Correct solution")
    else:
        print("Sadly, not quite right - see the problems below:")
        show_probs('Rows',row_probs)
        show_probs('Columns',col_probs)
        show_probs('Subsquares',sub_probs)
        show_probs('Cages',cage_probs)
        
def show_probs(name, probs):
    if len(probs) > 0:
        print(f'Problems with {name}')
        for p in probs:
            print(p)
        
def create_poly(cages, size):
    """Populates a polynomial representing the cage constraints.
    
    Creates all possible allocations of values to cells which
    satisfy the cage totals, and populates a polynomial in the form
    of a dictionary to hold these constaints.
    
    Args:
        cages(list): the Inputcages containing cell and target values
        size(int): the size of the puzzle (4 or 9)
        
    Returns:
        poly(dict): a dictionary keyed on variable names with their coefficients as values
    """
    side = int(math.sqrt(size))  

    perms = create_perms()
    patterns = generate_patterns(size)
    board = make_board(cages, patterns, side)
    
    poly = {}

    for cage in board:
        values = allocate_numbers(cage, perms)
        add_to_poly(poly, values)
        
    return poly

def solve(bqm):
    """Uses the KerberosSampler to produce a possible solution.
    
    Args:
        bqm (BinaryQuadraticModel): the model to be solved.
        
    Returns:
        (list): The best solution in the form of cell allocations.
                E.g. ['0,0_3','0,1_8', etc]
    """
    solution = KerberosSampler().sample(bqm, max_iter=10, convergence=3)
    best_solution = solution.first.sample

    result = []
    for k in best_solution:
        # we're only interested in the singleton values
        # which have the form 'n,m_v' of length 5
        if len(k) == 5 and best_solution[k] == 1:
            print(k, best_solution[k])
            result.append(k)
            
    return result

def create_board(result, size):
    """Converts the solver output to a square board and displays board 
    """
    board = [[0 for i in range(size)] for i in range(size)  ]

    for label in result:
        coord, digit = label.split('_')
        row, col = map(int, coord.split(','))

        board[row][col] = int(digit)

    for line in board:
        print(*line, sep=" ")  
        
    return board


def handle_args():
    """Determines a puzzle filename from the passed argument.
    
    If no argument is passed, a usage message is displayed.
    
    If '4' or '9' are provided, the sample puzzle of that size is used. 
    
    Otherwise, the first arg is assumed to be a puzzle filename unless it is less than 3 characters long.
    
    """
   # Either a filename or a board size (4 or 9) are accepted.
    ok = True
    filename = None
    
    if len(sys.argv) > 1:
        option = sys.argv[1]
        if option in ['4','9']:
            filename = f'easy_{option}.txt'
            print(f'\nUsing sample {filename} of size {option} x {option}.\n\n')
        elif len(option) < 3:
            ok = False
        else:
            filename = option
            print(f'\nAttempting to use {filename} as input board.\n\n')
    else:
        ok = False
        
    return ok, filename

def main():
    """Performs model creation, solving and solution checking.
    
    Args:
        problem (list): a list of strings representing the cages 
                        of the puzzle. One cage per line.
    """

    ok, filename = handle_args()
    if not ok:
        print('Usage: \n   python killer.py <board size> (valid board sizes are 4 and 9) or \n   python killer.py <filename> (where the board is included in the named file).\n\n')
        return
        
    # Read sudoku problem
    cages, size = read_puzzle(filename)
   
    poly = create_poly(cages, size)
    
    bqm = add_basic_constraints(poly, size)
    
    result = solve(bqm)
    
    board = create_board(result, size)
    
    check_solution(board, cages)


if __name__ == "__main__":

    main()