"""
动态参数优化模块 - Dynamic Parameter Optimization

支持：
- 网格搜索 (Grid Search)
- 遗传算法 (Genetic Algorithm)
- 贝叶斯优化 (Bayesian Optimization) - 预留接口
"""
import pandas as pd
import numpy as np
from typing import Dict, List, Callable, Any, Tuple
from dataclasses import dataclass
from concurrent.futures import ProcessPoolExecutor, as_completed
import logging
from datetime import datetime
import json
import random

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


@dataclass
class ParameterSpace:
    """参数空间定义"""
    name: str
    param_type: str  # 'int', 'float', 'choice'
    min_val: float = None
    max_val: float = None
    choices: List = None
    step: float = None
    
    def sample(self) -> Any:
        """随机采样一个值"""
        if self.param_type == 'int':
            return random.randint(int(self.min_val), int(self.max_val))
        elif self.param_type == 'float':
            return random.uniform(self.min_val, self.max_val)
        elif self.param_type == 'choice':
            return random.choice(self.choices)


@dataclass
class OptimizationResult:
    """优化结果"""
    best_params: Dict
    best_score: float
    all_results: List[Dict]
    optimization_time: float
    method: str


class GridSearchOptimizer:
    """
    网格搜索优化器
    
    对参数空间进行穷举搜索
    适合参数空间较小的情况
    """
    
    def __init__(self, strategy_class, param_spaces: Dict[str, ParameterSpace],
                 score_func: Callable, n_jobs: int = 4):
        self.strategy_class = strategy_class
        self.param_spaces = param_spaces
        self.score_func = score_func
        self.n_jobs = n_jobs
    
    def _generate_grid(self) -> List[Dict]:
        """生成参数网格"""
        param_names = list(self.param_spaces.keys())
        param_values = []
        
        for name in param_names:
            space = self.param_spaces[name]
            if space.param_type == 'int':
                values = list(range(int(space.min_val), int(space.max_val) + 1, 
                                  int(space.step or 1)))
            elif space.param_type == 'float':
                n_steps = int((space.max_val - space.min_val) / (space.step or 0.1))
                values = [space.min_val + i * (space.step or 0.1) 
                         for i in range(n_steps + 1)]
            elif space.param_type == 'choice':
                values = space.choices
            else:
                values = []
            param_values.append(values)
        
        # 笛卡尔积
        import itertools
        grid = []
        for combo in itertools.product(*param_values):
            grid.append(dict(zip(param_names, combo)))
        
        return grid
    
    def _evaluate_params(self, params: Dict, data: pd.DataFrame) -> Tuple[Dict, float]:
        """评估一组参数"""
        try:
            strategy = self.strategy_class(**params)
            score = self.score_func(strategy, data)
            return params, score
        except Exception as e:
            logger.error(f"参数评估失败 {params}: {e}")
            return params, -np.inf
    
    def optimize(self, data: pd.DataFrame, verbose: bool = True) -> OptimizationResult:
        """
        执行网格搜索
        
        Args:
            data: 回测数据
            verbose: 是否打印进度
            
        Returns:
            OptimizationResult
        """
        import time
        start_time = time.time()
        
        grid = self._generate_grid()
        logger.info(f"网格搜索: 共 {len(grid)} 组参数")
        
        results = []
        best_score = -np.inf
        best_params = None
        
        # 并行评估
        with ProcessPoolExecutor(max_workers=self.n_jobs) as executor:
            futures = {executor.submit(self._evaluate_params, params, data): params 
                      for params in grid}
            
            for i, future in enumerate(as_completed(futures)):
                params, score = future.result()
                results.append({'params': params, 'score': score})
                
                if score > best_score:
                    best_score = score
                    best_params = params
                
                if verbose and (i + 1) % 10 == 0:
                    logger.info(f"进度: {i+1}/{len(grid)}, 当前最佳: {best_score:.4f}")
        
        elapsed = time.time() - start_time
        
        # 按分数排序
        results.sort(key=lambda x: x['score'], reverse=True)
        
        return OptimizationResult(
            best_params=best_params,
            best_score=best_score,
            all_results=results,
            optimization_time=elapsed,
            method='grid_search'
        )


class GeneticOptimizer:
    """
    遗传算法优化器
    
    适合大参数空间，效率更高
    """
    
    def __init__(self, strategy_class, param_spaces: Dict[str, ParameterSpace],
                 score_func: Callable,
                 population_size: int = 50,
                 generations: int = 30,
                 crossover_rate: float = 0.8,
                 mutation_rate: float = 0.2,
                 elitism: int = 5):
        self.strategy_class = strategy_class
        self.param_spaces = param_spaces
        self.score_func = score_func
        self.population_size = population_size
        self.generations = generations
        self.crossover_rate = crossover_rate
        self.mutation_rate = mutation_rate
        self.elitism = elitism
    
    def _create_individual(self) -> Dict:
        """创建随机个体"""
        return {name: space.sample() 
                for name, space in self.param_spaces.items()}
    
    def _evaluate_fitness(self, individual: Dict, data: pd.DataFrame) -> float:
        """评估适应度"""
        try:
            strategy = self.strategy_class(**individual)
            return self.score_func(strategy, data)
        except Exception as e:
            logger.error(f"适应度评估失败: {e}")
            return -np.inf
    
    def _select_parent(self, population: List[Tuple[Dict, float]]) -> Dict:
        """锦标赛选择"""
        tournament_size = 3
        tournament = random.sample(population, min(tournament_size, len(population)))
        tournament.sort(key=lambda x: x[1], reverse=True)
        return tournament[0][0]
    
    def _crossover(self, parent1: Dict, parent2: Dict) -> Tuple[Dict, Dict]:
        """交叉操作"""
        if random.random() > self.crossover_rate:
            return parent1.copy(), parent2.copy()
        
        child1, child2 = {}, {}
        for key in parent1.keys():
            if random.random() < 0.5:
                child1[key] = parent1[key]
                child2[key] = parent2[key]
            else:
                child1[key] = parent2[key]
                child2[key] = parent1[key]
        
        return child1, child2
    
    def _mutate(self, individual: Dict) -> Dict:
        """变异操作"""
        mutated = individual.copy()
        
        for name, space in self.param_spaces.items():
            if random.random() < self.mutation_rate:
                mutated[name] = space.sample()
        
        return mutated
    
    def optimize(self, data: pd.DataFrame, verbose: bool = True) -> OptimizationResult:
        """
        执行遗传算法优化
        
        Args:
            data: 回测数据
            verbose: 是否打印进度
            
        Returns:
            OptimizationResult
        """
        import time
        start_time = time.time()
        
        # 初始化种群
        population = [(self._create_individual(), -np.inf) 
                     for _ in range(self.population_size)]
        
        all_results = []
        
        for generation in range(self.generations):
            # 评估适应度
            evaluated = []
            for individual, _ in population:
                fitness = self._evaluate_fitness(individual, data)
                evaluated.append((individual, fitness))
            
            # 排序
            evaluated.sort(key=lambda x: x[1], reverse=True)
            population = evaluated
            
            # 记录
            best_fitness = evaluated[0][1]
            avg_fitness = np.mean([f for _, f in evaluated if f != -np.inf])
            all_results.append({
                'generation': generation,
                'best': best_fitness,
                'avg': avg_fitness,
                'best_params': evaluated[0][0]
            })
            
            if verbose:
                logger.info(f"Gen {generation+1}/{self.generations}: "
                          f"Best={best_fitness:.4f}, Avg={avg_fitness:.4f}")
            
            # 精英保留
            new_population = evaluated[:self.elitism]
            
            # 生成下一代
            while len(new_population) < self.population_size:
                parent1 = self._select_parent(evaluated)
                parent2 = self._select_parent(evaluated)
                
                child1, child2 = self._crossover(parent1, parent2)
                child1 = self._mutate(child1)
                child2 = self._mutate(child2)
                
                new_population.append((child1, -np.inf))
                if len(new_population) < self.population_size:
                    new_population.append((child2, -np.inf))
            
            population = new_population
        
        elapsed = time.time() - start_time
        
        # 最终结果
        best_params = evaluated[0][0]
        best_score = evaluated[0][1]
        
        return OptimizationResult(
            best_params=best_params,
            best_score=best_score,
            all_results=all_results,
            optimization_time=elapsed,
            method='genetic_algorithm'
        )


class ParameterOptimizer:
    """
    参数优化统一接口
    
    根据参数空间大小自动选择优化方法
    """
    
    def __init__(self, strategy_class, score_func: Callable):
        self.strategy_class = strategy_class
        self.score_func = score_func
    
    def define_param_space(self, **kwargs) -> Dict[str, ParameterSpace]:
        """
        定义参数空间
        
        示例:
            optimizer.define_param_space(
                fast_period=ParameterSpace('fast_period', 'int', 5, 30, step=5),
                slow_period=ParameterSpace('slow_period', 'int', 20, 60, step=10),
                threshold=ParameterSpace('threshold', 'float', 0.01, 0.1, step=0.01)
            )
        """
        return kwargs
    
    def optimize(self, data: pd.DataFrame, param_spaces: Dict[str, ParameterSpace],
                 method: str = 'auto', **kwargs) -> OptimizationResult:
        """
        执行参数优化
        
        Args:
            data: 回测数据
            param_spaces: 参数空间定义
            method: 'grid', 'genetic', 'auto'(自动选择)
            **kwargs: 优化器特定参数
            
        Returns:
            OptimizationResult
        """
        # 估计参数组合数
        total_combinations = 1
        for space in param_spaces.values():
            if space.param_type == 'int':
                n = (space.max_val - space.min_val) // (space.step or 1) + 1
            elif space.param_type == 'float':
                n = 10  # 估计
            else:
                n = len(space.choices)
            total_combinations *= n
        
        # 自动选择方法
        if method == 'auto':
            if total_combinations <= 100:
                method = 'grid'
                logger.info(f"参数组合数 {total_combinations} 较少，使用网格搜索")
            else:
                method = 'genetic'
                logger.info(f"参数组合数 {total_combinations} 较多，使用遗传算法")
        
        # 执行优化
        if method == 'grid':
            optimizer = GridSearchOptimizer(
                self.strategy_class, param_spaces, self.score_func,
                n_jobs=kwargs.get('n_jobs', 4)
            )
        elif method == 'genetic':
            optimizer = GeneticOptimizer(
                self.strategy_class, param_spaces, self.score_func,
                population_size=kwargs.get('population_size', 50),
                generations=kwargs.get('generations', 30)
            )
        else:
            raise ValueError(f"未知优化方法: {method}")
        
        return optimizer.optimize(data, verbose=kwargs.get('verbose', True))
    
    @staticmethod
    def save_results(result: OptimizationResult, filepath: str):
        """保存优化结果"""
        data = {
            'best_params': result.best_params,
            'best_score': result.best_score,
            'method': result.method,
            'optimization_time': result.optimization_time,
            'timestamp': datetime.now().isoformat()
        }
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        logger.info(f"优化结果已保存: {filepath}")
    
    @staticmethod
    def load_results(filepath: str) -> Dict:
        """加载优化结果"""
        with open(filepath, 'r') as f:
            return json.load(f)


# 常用的评分函数
def sharpe_score(strategy, data: pd.DataFrame, risk_free_rate: float = 0.03) -> float:
    """
    基于夏普比率的评分
    
    需要策略返回signals后做简单回测计算收益
    """
    signals = strategy.generate_signals(data)
    
    if len(signals) < 2:
        return -np.inf
    
    # 简化的收益计算
    returns = []
    for i in range(1, len(signals)):
        if signals[i-1].action == 'buy':
            ret = (signals[i].price - signals[i-1].price) / signals[i-1].price
            returns.append(ret)
    
    if not returns:
        return -np.inf
    
    returns = np.array(returns)
    sharpe = (np.mean(returns) - risk_free_rate/252) / (np.std(returns) + 1e-8)
    
    return sharpe


def win_rate_score(strategy, data: pd.DataFrame) -> float:
    """
    基于胜率的评分
    """
    signals = strategy.generate_signals(data)
    
    if len(signals) < 2:
        return -np.inf
    
    wins = 0
    total = 0
    
    for i in range(1, len(signals)):
        if signals[i-1].action == 'buy' and signals[i].action == 'sell':
            profit = signals[i].price - signals[i-1].price
            if profit > 0:
                wins += 1
            total += 1
    
    if total == 0:
        return -np.inf
    
    return wins / total


def composite_score(strategy, data: pd.DataFrame, 
                   weights: Dict[str, float] = None) -> float:
    """
    综合评分
    
    组合多个指标：收益率、夏普比率、胜率、最大回撤
    """
    if weights is None:
        weights = {'return': 0.3, 'sharpe': 0.3, 'win_rate': 0.2, 'max_dd': 0.2}
    
    signals = strategy.generate_signals(data)
    
    if len(signals) < 4:
        return -np.inf
    
    # 简化的回测
    trades = []
    position = None
    
    for signal in signals:
        if signal.action == 'buy' and position is None:
            position = signal.price
        elif signal.action == 'sell' and position is not None:
            profit = signal.price - position
            trades.append(profit / position)
            position = None
    
    if len(trades) < 2:
        return -np.inf
    
    trades = np.array(trades)
    
    # 计算指标
    total_return = np.prod(1 + trades) - 1
    sharpe = np.mean(trades) / (np.std(trades) + 1e-8) * np.sqrt(252)
    win_rate = np.sum(trades > 0) / len(trades)
    
    # 最大回撤
    cumulative = np.cumprod(1 + trades)
    running_max = np.maximum.accumulate(cumulative)
    drawdown = (cumulative - running_max) / running_max
    max_dd = np.min(drawdown)
    
    # 综合得分
    score = (weights['return'] * total_return +
             weights['sharpe'] * sharpe / 5 +  # 归一化
             weights['win_rate'] * win_rate +
             weights['max_dd'] * (1 + max_dd))  # 回撤越小越好
    
    return score


if __name__ == "__main__":
    # 测试参数优化
    print("="*60)
    print("动态参数优化模块测试")
    print("="*60)
    
    # 生成测试数据
    import sys
    sys.path.insert(0, '/home/gem/workspace/agent/workspace/daily_stock_analysis')
    
    from strategies.examples import MACDStrategy
    
    np.random.seed(42)
    dates = pd.date_range('20240101', periods=200, freq='B')
    prices = 10 + np.random.randn(200).cumsum() * 0.5
    
    data = pd.DataFrame({
        'trade_date': dates.strftime('%Y%m%d'),
        'open': prices + np.random.randn(200) * 0.1,
        'high': prices + abs(np.random.randn(200)) * 0.2,
        'low': prices - abs(np.random.randn(200)) * 0.2,
        'close': prices,
        'vol': np.random.randint(10000, 100000, 200)
    })
    
    # 定义参数空间
    param_spaces = {
        'fast': ParameterSpace('fast', 'int', 8, 15),
        'slow': ParameterSpace('slow', 'int', 20, 30),
        'signal': ParameterSpace('signal', 'int', 7, 12)
    }
    
    # 创建优化器
    optimizer = GeneticOptimizer(
        MACDStrategy, param_spaces, win_rate_score,
        population_size=20, generations=10
    )
    
    print("\n开始遗传算法优化...")
    result = optimizer.optimize(data, verbose=True)
    
    print(f"\n优化完成!")
    print(f"最佳参数: {result.best_params}")
    print(f"最佳得分: {result.best_score:.4f}")
    print(f"耗时: {result.optimization_time:.2f}秒")
