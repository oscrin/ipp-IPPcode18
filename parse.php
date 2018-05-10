<?php
/* Faculty of Information Technology, Brno University of Technology
*  IPP (Principles of Programming Languages) - Project 1
*  Name: IPP parser of IPPcode18 language
*  Date created: February 2018
*  Author: Jan Kubica
*  Login: xkubic39
*  Email: xkubic39@stud.fit.vutbr.cz
*  File: parse.php - IPPcode18 language parser
*/

$comment_lines = 0;
$code_lines = 0;
$instructions = array();

$instruction_list = array(
    "MOVE" => "vs",
    "CREATEFRAME" => "",
    "PUSHFRAME" => "",
    "POPFRAME" => "",
    "DEFVAR" => "v",
    "CALL" => "l",
    "RETURN" => "",
    "PUSHS" => "s",
    "POPS" => "v",
    "ADD" => "vss",
    "SUB" => "vss",
    "MUL" => "vss",
    "IDIV" => "vss",
    "LT" => "vss",
    "GT" => "vss",
    "EQ" => "vss",
    "AND" => "vss",
    "OR" => "vss",
    "NOT" => "vs",
    "INT2CHAR" => "vs",
    "STRI2INT" => "vss",
    "READ" => "vt",
    "WRITE" => "s",
    "CONCAT" => "vss",
    "STRLEN" => "vs",
    "GETCHAR" => "vss",
    "SETCHAR" => "vss",
    "TYPE" => "vs",
    "LABEL" => "l",
    "JUMP" => "l",
    "JUMPIFEQ" => "lss",
    "JUMPIFNEQ" => "lss",
    "DPRINT" => "s",
    "BREAK" => ""
);

// -------------FUNCTIONS---------------

/* headline consists of ".IPPcode18" at the beginning */
function headline_check($line) {
	if (strlen($line) > 10) {
		if (strncasecmp($line,".IPPcode18", 10) == 0)
			return true;
		else
			return false;		
	}
	return false;
}

/* single line parsing */
function parse_line($line) {
	global $comment_lines;	// comments counter

	$line = preg_replace('/\n/', '', $line);	// remove line endings

	$no_comment = strstr($line, '#', true);		// checks line for comments

	if ($no_comment !== false) {	// if comments, increment counter
		$line = $no_comment;
		$comment_lines++;
	}

	$line = preg_replace('/^\s+/', '', $line);	// remove white spaces from beginning
	$line_arr = preg_split('/\s+/', $line);		// splits line in array

	$line_arr = array_filter($line_arr, "strlen"); // remove empty array values

	if (empty($line_arr)) {		// just comments or white spaces
		return false;
	}
	else {
		return $line_arr;	// line in array
	}
}

function print_help() {
	echo "IPPcode18 LANGUAGE PARSER\n";
	echo "It is implemented in PHP 5.6 and reads from stdin given source \ncode in IPPcode18. ";
	echo "The aim of the script is to process lexical \nand syntactic analysis over the given source code. ";
	echo "Script runs \nwithout any parameters, optionally gets '-h' or '--help'.\n";
	echo "Script takes input from stdin, output of the script is conver-\nted into XML, given back to stdout.\n";
	echo "Made by (c)Jan Kubica (xkubic39@stud.fit.vutbr.cz)\n";
	exit(0);
}

/* checks argument type (int, bool, string, label, type, var) */
function check_arg_type($type) { 
	
	$valid_frames = array("LF", "GF", "TF");
	$valid_types = array("string", "bool", "int");
	$check_array = array();
	$ret_val = array();

	$begin_name = strstr($type, '@', true);

	if ($begin_name !== false) {	// @ was found

		$end_name = strstr($type, '@');
		$end_name = substr($end_name, 1);

		// constant check
		if (in_array($begin_name, $valid_types)) { // string, bool, int

			if (strlen($end_name) === 0) { // nondeclared
				$ret_val[] = $begin_name;
				$ret_val[] = "";
				return $ret_val; // constant (int, bool, string)
			}
			switch ($begin_name) {
				case "string":
					$ret_val[] = $begin_name;
					// \xyz escape sequences
					$escape_check = str_split($end_name);
					for ($i = 0; $i < count($escape_check); $i++) {
						if (strcmp($escape_check[$i],"\\") === 0) {
							if (($i+3) > count($escape_check)) {
								return false;
							} else if (is_numeric($escape_check[$i+1]) && is_numeric($escape_check[$i+2]) && is_numeric($escape_check[$i+3])) {
								continue;
							} else {
								return false;
							}
						}
					}
					// <>&
					$xml_string = preg_replace('/&/', '&amp;', $end_name);
					$xml_string = preg_replace('/</', '&lt;', $xml_string);
					$xml_string = preg_replace('/>/', '&gt;', $xml_string);
					$ret_val[] = $xml_string;
					return $ret_val; // string
					break;
				case "bool":
					if (strcmp($end_name,"true") === 0 || strcmp($end_name,"false") === 0) {
						$ret_val[] = $begin_name;
						$ret_val[] = $end_name;
						return $ret_val; // bool
					} else {
						return false;
					}
					break;
				case "int":
					preg_match("/[+-]{0,1}[\d]+/", $end_name, $check_array);
					if (strcmp($check_array[0], $end_name) === 0) {
						$ret_val[] = $begin_name;
						$ret_val[] = $end_name;
						return $ret_val; // int
					} else {
						return false;
					}
					break;
				default:
					return false;
			}
		
		// variable check
		} else if (in_array($begin_name, $valid_frames)) { // LF, GF, TF
			
			// first character
			$first_ch = substr($end_name, 0, 1);
			if (is_numeric($first_ch)) {
				return false;
			}
			// rest of var name (aplhanumeric and [_, -, $, &, %, *])
			preg_match("/[a-zA-Z\d_\-\$&%*]*/", $end_name, $check_array);
			if (strcmp($check_array[0], $end_name) === 0) {
				$ret_val[] = "var";
				// <>&
				$xml_var = preg_replace('/&/', '&amp;', $type);
				$xml_var = preg_replace('/</', '&lt;', $xml_var);
				$xml_var = preg_replace('/>/', '&gt;', $xml_var);
				$ret_val[] = $xml_var;
				return $ret_val; // var_string
			}
			else {
				return false;
			}
		} else { // not constant or variable
			return false;
		}
	// label or type
	} else if (in_array($type, $valid_types)) {
		$ret_val[] = "type";
		$ret_val[] = $type;
		return $ret_val;
	} else {
		$first_ch = substr($type, 0, 1);
		if (is_numeric($first_ch)) { // label cannot start with number
			return false;
		}
		preg_match("/[a-zA-Z\d_\-\$&%*]*/", $type, $check_array);
		if (strcmp($check_array[0], $type) === 0) {
			$ret_val[] = "label";
			// <>&
			$xml_label = preg_replace('/&/', '&amp;', $type);
			$xml_label = preg_replace('/</', '&lt;', $xml_label);
			$xml_label = preg_replace('/>/', '&gt;', $xml_label);
			$ret_val[] = $xml_label;
			return $ret_val;
		}
		else {
			return false;
		}
	}
}

// -------------CLASSES---------------

class myException extends Exception {
  public function errorHandler() {
      $errMsg = "ERROR " . $this->getCode() . ": " . $this->getMessage() . "\n";
      fwrite(STDERR, $errMsg);
      exit($this->getCode());
  }
}

// class representing one Instruction with its arguments
class Instruction {
	public $instruction_type;
	public $operators_syntax;
	public $instruction_arguments = array();


	public function set_instruction($line_arr) { // gets array
		global $instruction_list;
		$inst = strtoupper($line_arr[0]);
		$found = false;
		foreach ($instruction_list as $key => $value) {
			if (strcmp($inst, $key) === 0) { // instruction found in list
				$this->instruction_type = $key;
				$this->operators_syntax = $value;
				$found = true;
			}
		}
		if ($found === true) {
			array_shift($line_arr);
			$this->instruction_arguments  = $line_arr;
		}
		return $found;
		
	}

	public function check_args_num($line_arr) {
		$defined_num_of_args = strlen($this->operators_syntax);
		$accepted_num_of_args = count($line_arr) -1;
		if ($accepted_num_of_args === $defined_num_of_args) {
			return true;
		} else {
			return false;
		}
	}

	public function check_arg_types() {
		global $instruction_list;
		// s, v, t, l
		$defined_args = str_split($instruction_list[$this->instruction_type]);
		$symbols = array( "int", "bool", "string", "var");

		$i = 0;

		if (strlen($instruction_list[$this->instruction_type]) === 0) {
			return true;
		}

		foreach($this->instruction_arguments as $a) {
			$a_type = check_arg_type($a);

			//(int, bool, string, label, type, var)
			switch ($defined_args[$i]) {
				case "s":
					if (in_array($a_type[0], $symbols)) {
						return true;
					} else {
						return false;
					}
				case "v":
					if ((strcmp($a_type[0], "var") === 0)) {
						return true;
					} else {
						return false;
					}
				case "t":
					if ((strcmp($a_type[0], "type") === 0)) {
						return true;
					} else {
						return false;
					}
				case "l":
					if ((strcmp($a_type[0], "label") === 0)) {
						return true;
					} else {
						return false;
					}
			}
		}
	}
}

try {
	if ($argc === 2 && ((in_array("-h", $argv) || in_array("--help", $argv) ) ) ) {
		print_help();
		exit(0);
	} else if ($argc >= 2) {
		throw new myException( 'Inconsistent parameters!', 10 );
	}
} catch (myException $e) {
	$e->errorHandler();
}

try {
	if ($argc === 1) {

		if (($stdin = fopen('php://stdin', 'r')) !== FALSE) {

			$line_num = 1;
			$line = fgets($stdin);

			if(!headline_check($line)) {
				throw new myException( 'Missing ".IPPcode18" at the beginning of source code!', 20 );
			}
			parse_line($line);

			while (($line = fgets($stdin)) !== false) {

				$line_num++;
				
				if (($line_arr = parse_line($line)) !== false) { // valid instruction
					$instruction = new Instruction;

					if ($instruction->set_instruction($line_arr) == false) {
						throw new myException( 'Not recognized instruction in line ' . $line_num . '.', 21 );
					}
					if ($instruction->check_args_num($line_arr) == false ) {
						throw new myException( 'Incorrect number of arguments in line ' . $line_num . '.', 21 );
					}
					if ($instruction->check_arg_types() == false ) {
						throw new myException( 'Incorrect type of arguments in line ' . $line_num . '.', 21 );
					}
					$instructions[] = $instruction;
					$code_lines++;
				}
			}
			fclose($stdin);
		} else {
			throw new myException( 'Cannot write to stdin!', 11 );
		}
	}
}
catch (myException $e) {
	$e->errorHandler();
}

/* Creating XML */

$dom = new DomDocument("1.0", "UTF-8");
$ipp18 = $dom->createElement('program');
$ipp18->setAttribute('language', 'IPPcode18');

// -------------------------------------------

$order_num = 1;
$arg_num = 1;
try {
	foreach($instructions as $i) {
		$xml_inst = $dom->createElement('instruction');
		$xml_inst->setAttribute('order', $order_num);
		$xml_inst->setAttribute('opcode', $i->instruction_type);

		if (count($i->instruction_arguments) > 0) {
			foreach($i->instruction_arguments as $o) {
				$t = check_arg_type($o);
				if ($t !== false) {
					$xml_op = $dom->createElement('arg' . $arg_num, $t[1]);
					$xml_op->setAttribute('type', $t[0]);
					$xml_inst->appendChild($xml_op);
					$arg_num++;
				} else {
					throw new myException('Invalid instruction argument!!!', 21);
				}
			}
		}
		$arg_num = 1;
		$ipp18->appendChild($xml_inst);
		$order_num++;
	}
} catch (myException $e) {
	$e->errorHandler();
}

$dom->appendChild($ipp18);
$dom->formatOutput = true;
$xmlData = $dom->saveXML();

echo $xmlData;

// echo "Comment lines: " . $comment_lines . "\n";
// echo "Code lines: " . $code_lines . "\n";

?>