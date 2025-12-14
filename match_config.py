"""
Match configuration module for LMS Cricket Simulator.
Defines match types, rules, and simulation parameters.
"""


class MatchConfig:
	"""Configuration for different match types and simulation settings."""
	
	# Match type definitions (for future expansion)
	MATCH_TYPES = {
		'T20': {
			'balls_per_innings': 120,  # 20 overs * 6 balls
			'balls_per_over': 6,
			'team_size': 11,
			'description': 'Twenty20 cricket'
		},
		'LMS': {
			'balls_per_innings': 100,  # 20 overs * 5 balls
			'balls_per_over': 5,
			'team_size': 8,
			'description': 'Last Man Standing format (5-ball overs). Batters retire at 50 runs and go to back of queue.',
			'retirement_threshold': 50
		},
		'OD': {
			'balls_per_innings': 300,  # 50 overs * 6 balls
			'balls_per_over': 6,
			'team_size': 11,
			'description': 'One Day format (50 overs)'
		},
		'FIRST_CLASS': {
			'balls_per_innings': None,  # no ball limit
			'balls_per_over': 6,
			'team_size': 11,
			'description': 'First-class cricket'
		}
	}
	
	# Simulation style presets (for future expansion)
	SIMULATION_STYLES = {
		'DEFAULT': {
			'description': 'Balanced simulation based on player stats',
			'randomness_factor': 1.0,
			'stat_weight': 1.0
		},
		'MATHEMATICAL': {
			'description': 'Heavily stats-driven, predictable outcomes',
			'randomness_factor': 0.5,
			'stat_weight': 1.5
		},
		'RANDOM': {
			'description': 'More unpredictable, less stats influence',
			'randomness_factor': 1.5,
			'stat_weight': 0.7
		},
		'WILD': {
			'description': 'Highly unpredictable, chaos mode',
			'randomness_factor': 2.0,
			'stat_weight': 0.5
		},
		'RNG': {
			'description': 'True RNG-based simulation, minimal stats influence',
			'randomness_factor': 2.0,
			'stat_weight': 0.0
		}
	}
	
	# Team mindset presets (for future expansion)
	TEAM_MINDSETS = {
		'BALANCED': {
			'description': 'Balanced approach',
			'aggression': 1.0,
			'risk_taking': 1.0
		},
		'CONSERVATIVE': {
			'description': 'Focus on preserving wickets',
			'aggression': 0.7,
			'risk_taking': 0.6
		},
		'AGGRESSIVE': {
			'description': 'Attack-focused batting',
			'aggression': 1.4,
			'risk_taking': 1.3
		},
		'BRUTAL': {
			'description': 'Maximum aggression, high risk',
			'aggression': 1.8,
			'risk_taking': 1.7
		},
		'BAZZBALL': {
			'description': 'Bazzball style',
			'aggression': 2.0,
			'risk_taking': 2.0
		}
	}
	
	def __init__(self, match_type='LMS', simulation_style='DEFAULT', team_mindset='BALANCED'):
		"""
		Initialize match configuration.
		
		Args:
			match_type: Type of match (T20, LMS, ODI, FIRST_CLASS)
			simulation_style: Simulation algorithm style (DEFAULT, MATHEMATICAL, RANDOM, WILD)
			team_mindset: Team approach (BALANCED, CONSERVATIVE, AGGRESSIVE, BRUTAL)
		"""
		self.match_type = match_type
		self.simulation_style = simulation_style
		self.team_mindset = team_mindset
		
		# Load match type settings
		if match_type not in self.MATCH_TYPES:
			raise ValueError(f"Unknown match type: {match_type}")
		
		match_settings = self.MATCH_TYPES[match_type]
		self.balls_per_innings = match_settings['balls_per_innings']
		self.balls_per_over = match_settings['balls_per_over']
		self.team_size = match_settings['team_size']
		
		# Load simulation style settings
		if simulation_style not in self.SIMULATION_STYLES:
			raise ValueError(f"Unknown simulation style: {simulation_style}")
		
		sim_settings = self.SIMULATION_STYLES[simulation_style]
		self.randomness_factor = sim_settings['randomness_factor']
		self.stat_weight = sim_settings['stat_weight']
		
		# Load team mindset settings
		if team_mindset not in self.TEAM_MINDSETS:
			raise ValueError(f"Unknown team mindset: {team_mindset}")
		
		mindset_settings = self.TEAM_MINDSETS[team_mindset]
		self.aggression = mindset_settings['aggression']
		self.risk_taking = mindset_settings['risk_taking']
	
	def get_overs_from_balls(self, balls):
		"""Convert balls to overs format (e.g., 5 balls with 5-ball overs = 1.0)."""
		overs = balls // self.balls_per_over
		balls_extra = balls % self.balls_per_over
		return f"{overs}.{balls_extra}"
	
	@classmethod
	def default(cls):
		"""Create a default configuration matching current prototype behavior."""
		return cls(match_type='LMS', simulation_style='DEFAULT', team_mindset='BALANCED')
	
	def __repr__(self):
		return (f"MatchConfig(type={self.match_type}, "
				f"style={self.simulation_style}, mindset={self.team_mindset})")
