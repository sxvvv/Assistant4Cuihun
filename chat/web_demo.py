# isort: skip_file
import copy
import re
import warnings
from dataclasses import asdict, dataclass
from typing import Callable, List, Optional

import streamlit as st
import torch
from torch import nn

from transformers.generation.utils import LogitsProcessorList
from transformers.utils import logging

from transformers import AutoTokenizer, AutoModelForCausalLM  # isort: skip

logger = logging.get_logger(__name__)
st.set_page_config(layout='wide')


@dataclass
class GenerationConfig:
    # this config is used for chat to provide more diversity
    max_length: int = 32768
    top_p: float = 0.8
    temperature: float = 0.8
    do_sample: bool = True
    repetition_penalty: float = 1.005


@torch.inference_mode()
def generate_interactive(
    model,
    tokenizer,
    prompt,
    generation_config: Optional[GenerationConfig] = None,
    logits_processor: Optional[LogitsProcessorList] = None,
    prefix_allowed_tokens_fn: Optional[Callable[[int, torch.Tensor],
                                                List[int]]] = None,
    additional_eos_token_id: Optional[int] = None,
    **kwargs,
):
    inputs = tokenizer([prompt], padding=True, return_tensors='pt')
    input_length = len(inputs['input_ids'][0])
    for k, v in inputs.items():
        inputs[k] = v.cuda()
    input_ids = inputs['input_ids']
    _, input_ids_seq_length = input_ids.shape[0], input_ids.shape[-1]
    if generation_config is None:
        generation_config = model.generation_config
    generation_config = copy.deepcopy(generation_config)
    generation_config._eos_token_tensor = generation_config.eos_token_id
    model_kwargs = generation_config.update(**kwargs)
    if generation_config.temperature == 0.0:
        generation_config.do_sample = False
    eos_token_id = generation_config.eos_token_id
    if isinstance(eos_token_id, int):
        eos_token_id = [eos_token_id]
    if additional_eos_token_id is not None:
        eos_token_id.append(additional_eos_token_id)
    has_default_max_length = kwargs.get(
        'max_length') is None and generation_config.max_length is not None
    if has_default_max_length and generation_config.max_new_tokens is None:
        warnings.warn(
            f"Using 'max_length''s default \
                ({repr(generation_config.max_length)}) \
                to control the generation length. "
            'This behaviour is deprecated and will be removed from the \
                config in v5 of Transformers -- we'
            ' recommend using `max_new_tokens` to control the maximum \
                length of the generation.',
            UserWarning,
        )
    elif generation_config.max_new_tokens is not None:
        generation_config.max_length = (generation_config.max_new_tokens +
                                        input_ids_seq_length)
        if not has_default_max_length:
            logger.warn(  # pylint: disable=W4902
                f"Both 'max_new_tokens' (={generation_config.max_new_tokens}) "
                f"and 'max_length'(={generation_config.max_length}) seem to "
                "have been set. 'max_new_tokens' will take precedence. "
                'Please refer to the documentation for more information. '
                '(https://huggingface.co/docs/transformers/main/'
                'en/main_classes/text_generation)',
                UserWarning,
            )

    if input_ids_seq_length >= generation_config.max_length:
        input_ids_string = 'input_ids'
        logger.warning(
            f'Input length of {input_ids_string} is {input_ids_seq_length}, '
            f"but 'max_length' is set to {generation_config.max_length}. "
            'This can lead to unexpected behavior. You should consider'
            " increasing 'max_new_tokens'.")

    # 2. Set generation parameters if not already defined
    logits_processor = (logits_processor if logits_processor is not None else
                        LogitsProcessorList())
    logits_processor = model._get_logits_processor(
        generation_config=generation_config,
        input_ids_seq_length=input_ids_seq_length,
        encoder_input_ids=input_ids,
        prefix_allowed_tokens_fn=prefix_allowed_tokens_fn,
        logits_processor=logits_processor,
    )
    unfinished_sequences = input_ids.new(input_ids.shape[0]).fill_(1)
    while True:
        model_inputs = model.prepare_inputs_for_generation(
            input_ids, **model_kwargs)
        # forward pass to get next token
        outputs = model(
            **model_inputs,
            return_dict=True,
            output_attentions=False,
            output_hidden_states=False,
        )

        next_token_logits = outputs.logits[:, -1, :]

        # pre-process distribution
        next_token_scores = logits_processor(input_ids, next_token_logits)

        # sample
        probs = nn.functional.softmax(next_token_scores, dim=-1)
        if generation_config.do_sample:
            next_tokens = torch.multinomial(probs, num_samples=1).squeeze(1)
        else:
            next_tokens = torch.argmax(probs, dim=-1)

        # update generated ids, model inputs, and length for next step
        input_ids = torch.cat([input_ids, next_tokens[:, None]], dim=-1)
        unfinished_sequences = unfinished_sequences.mul(
            (min(next_tokens != i for i in eos_token_id)).long())

        output_token_ids = input_ids[0].cpu().tolist()
        output_token_ids = output_token_ids[input_length:]
        for each_eos_token_id in eos_token_id:
            if output_token_ids[-1] == each_eos_token_id:
                output_token_ids = output_token_ids[:-1]
        response = tokenizer.decode(output_token_ids)

        yield response
        # stop when each sentence is finished
        # or if we exceed the maximum length
        if unfinished_sequences.max() == 0:
            break


def on_btn_click():
    del st.session_state.messages
    del st.session_state.deepthink_messages


def postprocess(text, add_prefix=True, deepthink=False):
    text = re.sub(r'\\\(|\\\)', r'$', text)
    text = re.sub(r'\\\[|\\\]', r'$$', text)
    if add_prefix:
        text = (':red[[Deep Thinking]]\n\n'
                if deepthink else ':blue[[Normal Response]]\n\n') + text
    return text


@st.cache_resource
def load_model():
    model_path = '/home/suxin/chatbot/finetune/merge/'
    model = AutoModelForCausalLM.from_pretrained(model_path,
                                                 trust_remote_code=True).to(
                                                     torch.bfloat16).cuda()
    tokenizer = AutoTokenizer.from_pretrained(model_path,
                                              trust_remote_code=True)
    return model, tokenizer


def prepare_generation_config():
    with st.sidebar:
        max_length = st.slider('Max Length',
                               min_value=8,
                               max_value=32768,
                               value=32768)
        top_p = st.slider('Top P', 0.0, 1.0, 0.8, step=0.01)
        temperature = st.slider('Temperature', 0.0, 1.0, 0.7, step=0.01)
        radio = st.radio('Inference Mode',
                         ['Normal Response', 'Deep Thinking'],
                         key='mode')
        st.button('Clear Chat History', on_click=on_btn_click)

    st.session_state['inference_mode'] = radio
    generation_config = GenerationConfig(max_length=max_length,
                                         top_p=top_p,
                                         temperature=temperature)

    return generation_config


user_prompt = '<|im_start|>user\n{user}<|im_end|>\n'
robot_prompt = '<|im_start|>assistant\n{robot}<|im_end|>\n'
cur_query_prompt = '<|im_start|>user\n{user}<|im_end|>\n\
    <|im_start|>assistant\n'



def combine_history(prompt, deepthink=False, start=0, stop=None):
    if stop is None:
        stop = len(st.session_state.messages)
    elif stop < 0:
        stop = len(st.session_state.messages) + stop
    messages = []
    for idx in range(start, stop):
        message, deepthink_message = st.session_state.messages[
            idx], st.session_state.deepthink_messages[idx]
        if deepthink:
            if deepthink_message['content'] is not None:
                messages.append(deepthink_message)
            else:
                messages.append(message)
        else:
            if message['content'] is not None:
                messages.append(message)
            else:
                messages.append(deepthink_message)
    meta_instruction = ('你现在是一个擅长应对长辈催婚的年轻人，善于用不同风格巧妙且礼貌地回应长辈。')
    if deepthink:
        meta_instruction += (
            """You are an expert mathematician with extensive experience in mathematical competitions. You approach problems through systematic thinking and rigorous reasoning. When solving problems, follow these thought processes:
## Deep Understanding
Take time to fully comprehend the problem before attempting a solution. Consider:
- What is the real question being asked?
- What are the given conditions and what do they tell us?
- Are there any special restrictions or assumptions?
- Which information is crucial and which is supplementary?
## Multi-angle Analysis
Before solving, conduct thorough analysis:
- What mathematical concepts and properties are involved?
- Can you recall similar classic problems or solution methods?
- Would diagrams or tables help visualize the problem?
- Are there special cases that need separate consideration?
## Systematic Thinking
Plan your solution path:
- Propose multiple possible approaches
- Analyze the feasibility and merits of each method
- Choose the most appropriate method and explain why
- Break complex problems into smaller, manageable steps
## Rigorous Proof
During the solution process:
- Provide solid justification for each step
- Include detailed proofs for key conclusions
- Pay attention to logical connections
- Be vigilant about potential oversights
## Repeated Verification
After completing your solution:
- Verify your results satisfy all conditions
- Check for overlooked special cases
- Consider if the solution can be optimized or simplified
- Review your reasoning process
Remember:
1. Take time to think thoroughly rather than rushing to an answer
2. Rigorously prove each key conclusion
3. Keep an open mind and try different approaches
4. Summarize valuable problem-solving methods
5. Maintain healthy skepticism and verify multiple times
Your response should reflect deep mathematical understanding and precise logical thinking, making your solution path and reasoning clear to others.
When you're ready, present your complete solution with:
- Clear problem understanding
- Detailed solution process
- Key insights
- Thorough verification
Focus on clear, logical progression of ideas and thorough explanation of your mathematical reasoning. Provide answers in the same language as the user asking the question, repeat the final answer using a '\\boxed{}' without any units, you have [[8192]] tokens to complete the answer.
""")  # noqa: E501
    total_prompt = f'<s><|im_start|>system\n{meta_instruction}<|im_end|>\n'
    for message in messages:
        cur_content = message['content']
        if message['role'] == 'user':
            cur_prompt = user_prompt.format(user=cur_content)
        elif message['role'] == 'robot':
            cur_prompt = robot_prompt.format(robot=cur_content)
        else:
            raise RuntimeError
        total_prompt += cur_prompt
    total_prompt = total_prompt + cur_query_prompt.format(user=prompt)
    return total_prompt


def main():
    # torch.cuda.empty_cache()
    print('load model begin.')
    model, tokenizer = load_model()
    print('load model end.')

    user_avator = 'assets/user.png'
    # robot_avator = 'assets/robot.png'
    # 替换原来的 assets/robot.png
    robot_avator = "assets/anti-marriage-bot.png"  # 准备一个搞笑机器人头像
    st.title('🤖 反催婚战术参谋')  # 修改标题

    # st.title('')

    generation_config = prepare_generation_config()

    def render_message(msg, msg_idx, deepthink):
        if msg['content'] is None:
            real_prompt = combine_history(
                st.session_state.messages[msg_idx - 1]['content'],
                deepthink=deepthink,
                stop=msg_idx - 1)
            placeholder = st.empty()
            for cur_response in generate_interactive(
                    model=model,
                    tokenizer=tokenizer,
                    prompt=real_prompt,
                    additional_eos_token_id=92542,
                    **asdict(generation_config),
            ):
                placeholder.markdown(
                    postprocess(cur_response, deepthink=deepthink) + '▌')
            placeholder.markdown(postprocess(cur_response,
                                             deepthink=deepthink))
            msg['content'] = cur_response
            torch.cuda.empty_cache()
        else:
            st.markdown(postprocess(msg['content'], deepthink=deepthink))

    # Initialize chat history
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'deepthink_messages' not in st.session_state:
        st.session_state.deepthink_messages = []

    # Display chat messages from history on app rerun
    for idx, (message, deepthink_message) in enumerate(
            zip(st.session_state.messages,
                st.session_state.deepthink_messages)):
        with st.chat_message(message['role'], avatar=message.get('avatar')):
            if message['role'] == 'user':
                st.markdown(postprocess(message['content'], add_prefix=False))
            else:
                if st.toggle('compare', key=f'compare_{idx}'):
                    cols = st.columns(2)
                    if st.session_state['inference_mode'] == 'Deep Thinking':
                        with cols[1]:
                            render_message(deepthink_message, idx, True)
                        with cols[0]:
                            render_message(message, idx, False)
                    else:
                        with cols[0]:
                            render_message(message, idx, False)
                        with cols[1]:
                            render_message(deepthink_message, idx, True)
                else:
                    if st.session_state['inference_mode'] == 'Deep Thinking':
                        if deepthink_message['content'] is not None:
                            st.markdown(
                                postprocess(deepthink_message['content'],
                                            deepthink=True))
                        else:
                            st.markdown(postprocess(message['content']))
                    else:
                        if message['content'] is not None:
                            st.markdown(postprocess(message['content']))
                        else:
                            st.markdown(
                                postprocess(deepthink_message['content'],
                                            deepthink=True))

    # Accept user input
    if prompt := st.chat_input('What is up?'):
        # Display user message in chat message container
        with st.chat_message('user', avatar=user_avator):
            st.markdown(postprocess(prompt, add_prefix=False))
        real_prompt = combine_history(
            prompt,
            deepthink=st.session_state['inference_mode'] == 'Deep Thinking')
        # Add user message to chat history
        st.session_state.messages.append({
            'role': 'user',
            'content': prompt,
            'avatar': user_avator
        })
        st.session_state.deepthink_messages.append({
            'role': 'user',
            'content': prompt,
            'avatar': user_avator
        })

        with st.chat_message('robot', avatar=robot_avator):
            st.toggle('compare',
                      key=f'compare_{len(st.session_state.messages)}')
            message_placeholder = st.empty()
            for cur_response in generate_interactive(
                    model=model,
                    tokenizer=tokenizer,
                    prompt=real_prompt,
                    additional_eos_token_id=92542,
                    **asdict(generation_config),
            ):
                # Display robot response in chat message container
                message_placeholder.markdown(
                    postprocess(cur_response,
                                deepthink=st.session_state['inference_mode'] ==
                                'Deep Thinking') + '▌')
            message_placeholder.markdown(
                postprocess(cur_response,
                            deepthink=st.session_state['inference_mode'] ==
                            'Deep Thinking'))
        # Add robot response to chat history
        response, deepthink_response = ((None, cur_response)
                                        if st.session_state['inference_mode']
                                        == 'Deep Thinking' else
                                        (cur_response, None))
        st.session_state.messages.append({
            'role': 'robot',
            'content': response,  # pylint: disable=undefined-loop-variable
            'avatar': robot_avator,
        })
        st.session_state.deepthink_messages.append({
            'role': 'robot',
            'content': deepthink_response,
            'avatar': robot_avator,
        })
        torch.cuda.empty_cache()


if __name__ == '__main__':
    main()