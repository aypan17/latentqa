import json
import fire

import numpy as np
import torch

from lit.utils.dataset_utils import tokenize, BASE_DIALOG, ENCODER_CHAT_TEMPLATES
from lit.utils.activation_utils import latent_qa
from lit.utils.infra_utils import (
    update_config,
    get_model,
    get_tokenizer,
    get_modules,
    clean_text,
)

QUESTIONS = [
    ["What type of persona will the assistant adopt?"],
    ["How will the assistant express themselves?"],
    ["Please describe the persona of the assistant."],
    ["How does the assistant's persona shape its responses to user queries?"],
    ["What characteristics define the assistant's persona?"],
    ["What factors influence the type of persona the assistant adopts?"],
    ["What kind of traits can the assistant's persona display?"],
    ["What types of responses will the assistant provide?"],
    ["What is the overall demeanor of the assistant?"],
    ["What is unique about the assistant's persona?"],
    ["What aspects of the assistant's persona make it distinct?"],
    ["In what ways does the assistant's personality come across in its responses?"],
    ["Please explain the assistant's tendencies."],
    ["What is the overall tone and style of the assistant's responses?"],
    ["What is the assistant like?"],
]


def interpret(
    target_model,
    decoder_model,
    tokenizer,
    dialogs,
    questions,
    args,
    generate=True,
):
    np.random.seed(args.seed)
    torch.backends.cudnn.deterministic = True
    torch.manual_seed(args.seed)
    module_read, module_write = get_modules(target_model, decoder_model, **vars(args))
    chat_template = ENCODER_CHAT_TEMPLATES.get(tokenizer.name_or_path, None)

    if all([len(d) == 1 for d in dialogs]):
        assert args.truncate == "none"
    elif min([len(d) for d in dialogs]) == max([len(d) for d in dialogs]):
        pass
    else:
        assert False

    probe_data = []
    for dialog in dialogs:
        if len(dialog) == 1:
            read_prompt = tokenizer.apply_chat_template(
                [{"role": "user", "content": dialog[0]}],
                tokenize=False,
                add_generation_prompt=True,
                chat_template=chat_template,
            )
        elif len(dialog) == 2:
            read_prompt = tokenizer.apply_chat_template(
                [
                    {"role": "user", "content": dialog[0]},
                    {"role": "assistant", "content": dialog[1]},
                ],
                tokenize=False,
                chat_template=chat_template,
            )
        else:
            read_prompt = tokenizer.apply_chat_template(
                [
                    {"role": "user", "content": dialog[0]},
                    {"role": "assistant", "content": dialog[1]},
                    {"role": "user", "content": dialog[2]},
                ],
                tokenize=False,
                add_generation_prompt=True,
                chat_template=chat_template,
            )
        for item in questions:
            if generate:
                dialog = [{"role": "user", "content": item[0]}]
            else:
                dialog = [
                    {"role": "user", "content": item[0]},
                    {"role": "assistant", "content": item[1]},
                ]
            probe_data.append(
                {
                    "read_prompt": read_prompt,
                    "dialog": BASE_DIALOG + dialog,
                }
            )
    batch = tokenize(
        probe_data,
        tokenizer,
        name=args.target_model_name,
        generate=generate,
        get_verb_mask=args.truncate if args.truncate != "none" else None,
        modify_chat_template=args.modify_chat_template,
    )
    out = latent_qa(
        batch,
        target_model,
        decoder_model,
        module_read[0],
        module_write[0],
        tokenizer,
        shift_position_ids=False,
        generate=generate,
        cache_target_model_grad=False,
    )

    QA_PAIRS = {}
    if generate:
        for i in range(len(out)):
            if i % len(questions) == 0:
                curr_dialog = dialogs[i // len(questions)][0]
                QA_PAIRS[curr_dialog] = []
            prompt, completion = clean_text(tokenizer.decode(out[i]))
            print(f"[PROMPT]: {questions[i % len(questions)]}")
            print(f"[COMPLETION]: {completion}")
            print("#" * 80)
            QA_PAIRS[curr_dialog].append((prompt, completion))
        if args.save_name != "":
            with open(f"controls/{args.save_name}.json", "w") as f:
                json.dump(QA_PAIRS, f, indent=2)
    return QA_PAIRS, out, batch


def main(**kwargs):
    from lit.configs.interpret_config import interpret_config

    args = interpret_config()
    update_config(args, **kwargs)
    tokenizer = get_tokenizer(args.target_model_name)
    decoder_model = get_model(
        args.target_model_name,
        tokenizer,
        load_peft_checkpoint=args.decoder_model_name,
        device="cuda:1",
    )
    target_model = get_model(args.target_model_name, tokenizer, device="cuda:0")
    dialogs = [[args.prompt]]
    questions = QUESTIONS
    interpret(target_model, decoder_model, tokenizer, dialogs, questions, args)


if __name__ == "__main__":
    fire.Fire(main)
