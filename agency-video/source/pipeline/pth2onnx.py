"""Convert Real-ESRGAN SRVGGNetCompact .pth weights to ONNX without torch."""
import sys, zipfile, pickle, numpy as np, onnx
from onnx import helper, TensorProto, numpy_helper

src, dst = sys.argv[1], sys.argv[2]
z = zipfile.ZipFile(src)
prefix = z.namelist()[0].split('/')[0]

def rebuild(storage, offset, size, stride, *a):
    return np.lib.stride_tricks.as_strided(storage[offset:], shape=tuple(size), strides=tuple(s * 4 for s in stride)).copy()

class U(pickle.Unpickler):
    def find_class(self, mod, name):
        if mod == 'torch._utils' and name == '_rebuild_tensor_v2':
            return rebuild
        if mod == 'torch' and name.endswith('Storage'):
            return name
        if mod == 'collections' and name == 'OrderedDict':
            import collections; return collections.OrderedDict
        raise pickle.UnpicklingError(f'blocked {mod}.{name}')
    def persistent_load(self, pid):
        _, stype, key, loc, numel = pid
        assert stype == 'FloatStorage', stype
        return np.frombuffer(z.read(f'{prefix}/data/{key}'), dtype=np.float32)

sd = U(z.open(f'{prefix}/data.pkl')).load()
sd = sd.get('params_ema', sd.get('params', sd))
keys = sorted({int(k.split('.')[1]) for k in sd}, key=int)
print('layers', len(keys), 'first', sd['body.0.weight'].shape, 'last', sd[f'body.{keys[-1]}.weight'].shape)

inits, nodes = [], []
cur = 'x'
for i in keys:
    w = sd[f'body.{i}.weight']
    if w.ndim == 4:
        inits += [numpy_helper.from_array(w, f'w{i}'), numpy_helper.from_array(sd[f'body.{i}.bias'], f'b{i}')]
        nodes.append(helper.make_node('Conv', [cur, f'w{i}', f'b{i}'], [f'c{i}'], pads=[1, 1, 1, 1], kernel_shape=[3, 3]))
        cur = f'c{i}'
    else:
        inits.append(numpy_helper.from_array(w.reshape(-1, 1, 1), f's{i}'))
        nodes.append(helper.make_node('PRelu', [cur, f's{i}'], [f'p{i}']))
        cur = f'p{i}'
r = int(round((sd[f'body.{keys[-1]}.weight'].shape[0] / 3) ** 0.5))
nodes.append(helper.make_node('DepthToSpace', [cur], ['ps'], blocksize=r, mode='CRD'))
inits.append(numpy_helper.from_array(np.array([1, 1, r, r], np.float32), 'scales'))
nodes.append(helper.make_node('Resize', ['x', '', 'scales'], ['base'], mode='nearest'))
nodes.append(helper.make_node('Add', ['ps', 'base'], ['y']))
g = helper.make_graph(nodes, 'srvgg',
                      [helper.make_tensor_value_info('x', TensorProto.FLOAT, [1, 3, 'H', 'W'])],
                      [helper.make_tensor_value_info('y', TensorProto.FLOAT, [1, 3, 'H4', 'W4'])], inits)
m = helper.make_model(g, opset_imports=[helper.make_opsetid('', 17)]); m.ir_version = 9
onnx.checker.check_model(m)
onnx.save(m, dst)
print('saved', dst, 'scale', r)
