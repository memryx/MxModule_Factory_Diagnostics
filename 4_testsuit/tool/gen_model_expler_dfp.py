import sys
import os
mix_home = os.getenv('MIX_HOME')
if mix_home == None:
    print("MIX_HOME is not defined; 'source /path/to/mix/setup_env.sh' to\
           define or export using 'export MIX_HOME=/path/to/mix'")
    exit(1)
sys.path.append(mix_home)

from memryx import NeuralCompiler, Benchmark
from pathlib import Path
from multiprocessing import Pool
import gc
import argparse

def parse():
    parser = argparse.ArgumentParser(
                description = "\033[34m model loader\033[0m",
                formatter_class = argparse.RawDescriptionHelpFormatter)

    control = parser.add_argument_group("Control")
    control.add_argument("-f",
                        dest = "fname",
                        type=str,
                        default = 'test.txt',
                        help    = "model exploer testcase name file")

    cmd_args = parser.parse_args()

    return cmd_args

class model_loader:

    def __init__(self):
        self.results = []

    def load_model_list_from_txt(self, fname):
        model_list = []
        with open(fname, "r") as f:
            for line in f.readlines(): 
                line = line.strip()
                model_list.append(line)
        return model_list
        
    def find_ori_model_file(self, model_dir):
        api_lut = ["onnx_model_0.onnx", "tflite_model_0.tflite", "tf_model_0.pb" , "keras_model_0.h5"]
        ori_model_file = ''
        for i, api in enumerate(api_lut):
            if(Path(model_dir, api).exists()):
                ori_model_file = model_dir+'/'+api
        return ori_model_file
    
    def find_compiled_dfp(self, model_dir):
        dfp = ''
        if(Path(model_dir, 'model.dfp').exists()):
            dfp = model_dir+'/'+'model.dfp'
        return dfp

    def process_result(self, result):
        self.results.append(result)
        print(result['model_dir'], result['fps'])
        
    def run_model(self, model_dir): 
        ori_model_file = self.find_ori_model_file(model_dir)
        comipled_dfp = ''
        comipled_dfp = self.find_compiled_dfp(model_dir)
        fps = -1
        result = dict(model_dir=model_dir, fps=fps)
        
        dfp = None
        if comipled_dfp == '':
            if ori_model_file == '':
                result['fps'] = 'model not found'
                print('{} original model file not found'.format(model_dir))
                return result

            nc = NeuralCompiler(models=ori_model_file, 
                                num_chips='2', 
                                chip_gen='3.1',
                                input_format='BF16',
                                output_format='GBF80',
                                dfp_fname='model.dfp',
                                autocrop=True,
                                hw_dfp_path=model_dir+'/',
                                no_sim_dfp=True,
                                verbose=1)
            try:
                dfp = nc.run()
            except Exception as e:
                result['fps'] = str(e)
        else:
            with open(comipled_dfp, 'rb') as f:
                dfp = comipled_dfp
            
        if dfp is not None:
            print('{} compile done'.format(model_dir))
            #with Benchmark(dfp=dfp) as bench:
            #    _, _, fps = bench.run(frames=500, threading=True)
            result['fps'] = 0

        return result

    def run(self, fname):
        model_list = self.load_model_list_from_txt(fname)
        # model_list = [
        #     # 'model_explorer_42io_esp32_kws_GitHub',
        #     # 'model_explorer_eFiniLan_legacypilot_GitHub',
        #     # 'model_explorer_ersilia-os_image-based-dl_GitHub',
        #     # 'model_explorer_kayou11_Projet-Datascience_GitHub',
        #     # 'model_explorer_openvinotoolkit_openvino_GitHub_24',
        #     # 'model_explorer_tensil-ai_tensil-models_GitHub_2',
        # ]
        async_results = []

        try:
            with Pool(4) as pool:
                for j in range(0, len(model_list)):
                    async_res = pool.apply_async(self.run_model, kwds={'model_dir': model_list[j]},callback=self.process_result)
                    async_results.append(async_res)
                pool.close()
                [res.get() for res in async_results]
        except KeyboardInterrupt:
            self.write_all_result_file()
            pool.close()
            pool.terminate()
            gc.collect()
            

    def write_all_result_file(self):
        result_file = 'model_explorer_perf_result.csv'
        with open(result_file, 'w') as f:
            f.write('{},{}\n'.format("Model", "FPS"))
            for i, result in enumerate(self.results):
                f.write('{},{}\n'.format(result['model_dir'], result['fps']))

                
def main():
    cmd_arg = parse()
    loader = model_loader()
    loader.run(cmd_arg.fname)
    #loader.write_all_result_file()
    gc.collect()

if __name__=="__main__":
    main()
    
