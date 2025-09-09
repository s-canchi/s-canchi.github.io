---
layout: post
title: Personalize Zsh Prompt
subtitle: Tweaking the zsh prompt using Oh My Zsh 
tags: [Zsh, Oh My Zsh, Command Prompt]
comments: true
---

In this post, I will highlight some of the ways in which you can manipulate the information displayed as part of the command prompt.
The default shell in all Apple computers and laptops changed to zsh from macOS Catalina and onwards. Zsh is a specific type of shell just as macOS is a specific type of operating system. Other popular shell varieties include bash, cshell, powershell etc.

[Oh My Zsh](https://ohmyz.sh){:target="_blank"} is the Zsh package manager which allows you to manage the different zsh configurations, plugins and themes to enhance the look and functionality of the Zsh shell.

{: .box-note}
**Note:** All the instructions are written and tested on macOS Monterey (v12.0.1).

## Step 1: Install Oh My Zsh

You can check the type and version of the shell to confirm if you have zsh.

```bash
$ echo $SHELL
/bin/zsh
$ $SHELL --version
zsh 5.x
```

If you do not have zsh, you can get started with first installing it using one of many package managers. It is available on conda and can be installed using:

```bash
$ conda install -c conda-forge zsh
```
To set zsh as the default shell, run:

```bash
$ chsh -s /bin/zsh
```

Follow one of the methods listed in README for [Oh My Zsh](https://github.com/ohmyzsh/ohmyzsh#basic-installation){:target="_blank"} to install it.

## Step 2: Customize configuration

The primary file you would work with is `.zshrc` located in your home folder `~`. Since it is a hidden file, you can first check if this file exists.

```bash
$ ls -a ~
```
You can also open an empty document and copy the contents of the [zshrc template file](https://github.com/ohmyzsh/ohmyzsh/blob/master/templates/zshrc.zsh-template){:target="_blank"} to get started.

Oh My Zsh offers many [themes](https://github.com/ohmyzsh/ohmyzsh/wiki/Themes){:target="_blank"}. Open the `.zshrc` using any text editor, update the value for `ZSH_THEME` to the one you prefer, save and exit. The default is set to `robbyrussell`. To get a local list of all the themes, run:

```bash
$ ls -a ~/.oh-my-zsh/themes
```

For the changes to take effect, you can either start a new terminal window or run:

```bash
$ source ~/.zshrc
```

Similar to the themes, there are a wide variety of plugins available. You can check the complete list on the [Wiki page](https://github.com/ohmyzsh/ohmyzsh/wiki/Plugins-Overview){:target="_blank"} or locally using:

```bash
$ ls -a ~/.oh-my-zsh/plugins
```

Update the values in the `plugins` variable in the `~/.zshrc` file to the ones you prefer. For example:

```bash
plugins=(git brew macos colored-man-pages)
```

Remember to save any changes you make to the configuration file and update the shell for the changes to take effect.

```bash
$ source ~/.zshrc
```

## Step 3: Customize virtualenv information

Typically virtual environments prepend the command prompt.

```bash
(virtualenv) $
```

To be able to view this information on a Oh My Zsh theme, we need to follow a few steps. Go to the configuration file and add `virtualenv` to the plugins list.

```bash
plugins=(git brew macos colored-man-pages virtualenv)
```

At the end of the `.zshrc` file on a new line copy the following lines, save and exit.

```bash
function virtualenv_info {
 [ $CONDA_PROMPT_MODIFIER ] && echo `basename $CONDA_PROMPT_MODIFIER`
}
```

{: .box-note}
**Note:** The above function is specific to conda. Replace the `CONDA_PROMPT_MODIFIER` with `VIRTUAL_ENV` for all other virtual environment managers.

Next access the specific theme file. I am using pygmalion as the example.

```bash
 $ nano ~/.oh-my-zsh/themes/pygmalion.zsh-theme
```

Variables `base_prompt` and `post_prompt` are declared at the top of the file. Add a new variable to define the conda virtualenv information.

```bash
conda_env='%{$fg[magenta]%}$CONDA_PROMPT_MODIFIER%{$reset_color%}'
```

Scroll to the end of the page to find the `prompt_pygmalion_precmd()` function:

```bash
prompt_pygmalion_precmd(){
  setopt localoptions nopromptsubst extendedglob

  local gitinfo=$(git_prompt_info)
  local gitinfo_nocolor=${gitinfo//\%\{[^\}]##\}}
  local exp_nocolor="$(print -P \"${base_prompt_nocolor}${gitinfo_nocolor}${post_prompt_nocolor}\")"
  local prompt_length=${#exp_nocolor}

  PROMPT="${base_prompt}${gitinfo}${post_prompt}"  
}
```
Modify the `PROMPT` variable within the function to include the newly created variable:

```bash
  PROMPT="${conda_env}${base_prompt}${gitinfo}${post_prompt}"
```

Save and exit from the theme file. Subsequently update the shell by running `source ~/.zshrc`. The command will now display the virtualenv information along with all the previously displayed information.

```bash
(base) $
```

## Step 4: Modify prompt without theme support

Although there are many themes, not all support the display of the virtualenv information by modifying the theme file as shown in Step 3.
In those cases, you can define the prompt with all the information you would like displayed and add it to the `~/.zshrc` file.

{: .box-note}
**Note:** You need to comment out the `PROMPT` variable in the theme file for the custom prompt settings to apply.

Add the following line to `.zshrc` file:

```bash
PROMPT='%{$fg[magenta]%}$(virtualenv_info)%{$reset_color%} %{$fg[cyan]%}%3~%{$reset_color%}|$(git_prompt_info)$ '
```

In zsh, `%` and `)` are special characters. The `fg` signifies the foreground color. The `%3~` shows the path of the current working directory at three levels depth. If you prefer the full path relative to the home directory to be shown you can update it to `%0~`. The `(git_prompt_info)` points towards the currently checked out git branch for the repository.
Save and exit the `.zshrc`. To see the changes take effect, run:

```bash
source ~/.zshrc
```

Ultimately, there are many options to customize the command prompt to appeal to your aesthetic taste and to display the information you find most useful. Hopefully this post helps decode some aspects of it. Happy tweaking!
