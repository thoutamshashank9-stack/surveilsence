import os
import onnx
from onnx import helper, TensorProto
from app.core.logging import get_logger

logger = get_logger(__name__)

class DirectMLGraphSurgeon:
    """
    Graph surgeon to patch ONNX models for DirectML compatibility.
    
    DirectML lacks native support for Int64 indices in Gather, ScatterND, TopK, 
    and NonZero operators. This class performs targeted graph surgery to downcast 
    only these indices to Int32, avoiding E_INVALIDARG crashes while keeping shape-defining 
    attributes as Int64 to satisfy the ONNX validator.
    """

    @staticmethod
    def patch_model_for_dml(model_path: str, output_path: str) -> str:
        """
        Loads an ONNX model, performs selective Int64 -> Int32 downcasting for 
        indices inputs of Gather, ScatterND, TopK, and NonZero operators, and 
        saves the patched model.
        """
        if not os.path.exists(model_path):
            logger.error("Model path does not exist for graph surgery", path=model_path)
            return model_path

        try:
            logger.info("Starting DirectML graph surgery", input_model=model_path, output_model=output_path)
            model = onnx.load(model_path)
            graph = model.graph

            # Track initializers that are Int64
            initializers = {init.name: init for init in graph.initializer}
            value_infos = {val.name: val for val in graph.value_info}
            inputs = {inp.name: inp for inp in graph.input}

            # Map operator name -> indices inputs index that needs downcasting
            TARGET_OPS = {
                "Gather": 1,      # Gather(data, indices)
                "ScatterND": 1,   # ScatterND(data, indices, updates)
                "TopK": 1,        # TopK(x, k)
                "NonZero": 0      # NonZero(x)
            }

            cast_node_count = 0

            # List to hold new cast nodes
            new_nodes = []

            for node in graph.node:
                if node.op_type in TARGET_OPS:
                    idx_to_cast = TARGET_OPS[node.op_type]
                    if idx_to_cast < len(node.input):
                        input_name = node.input[idx_to_cast]
                        
                        # Determine if the input is indeed Int64
                        is_int64 = False
                        
                        if input_name in initializers:
                            init = initializers[input_name]
                            if init.data_type == TensorProto.INT64:
                                is_int64 = True
                        elif input_name in value_infos:
                            val = value_infos[input_name]
                            if val.type.tensor_type.elem_type == TensorProto.INT64:
                                is_int64 = True
                        elif input_name in inputs:
                            inp = inputs[input_name]
                            if inp.type.tensor_type.elem_type == TensorProto.INT64:
                                is_int64 = True

                        if is_int64:
                            # We need to insert a Cast node (INT64 -> INT32)
                            cast_output_name = f"{input_name}_dml_cast_int32"
                            
                            cast_node = helper.make_node(
                                "Cast",
                                inputs=[input_name],
                                outputs=[cast_output_name],
                                name=f"dml_cast_node_{cast_node_count}",
                                to=TensorProto.INT32
                            )
                            new_nodes.append(cast_node)
                            
                            # Replace input in target node
                            node.input[idx_to_cast] = cast_output_name
                            cast_node_count += 1
                
                new_nodes.append(node)

            # Rebuild graph nodes list
            del graph.node[:]
            graph.node.extend(new_nodes)

            # Save the patched model
            os.makedirs(os.path.dirname(output_path), exist_ok=True)
            onnx.save(model, output_path)
            logger.info("DirectML graph surgery completed successfully", cast_nodes_added=cast_node_count)
            return output_path

        except Exception as e:
            logger.error("DirectML graph surgery failed, falling back to original model", error=str(e))
            return model_path
