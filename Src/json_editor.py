# json_editor.py - 可视化 JSON 编辑器

import os
import sys
import json
from functools import partial
from PyQt5.QtCore import Qt
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout,
    QHBoxLayout, QPushButton,QTreeWidget, QTreeWidgetItem,
    QMessageBox, QAbstractItemView,QMenu, QAction, QTextEdit
    )
from loguru import logger

class JSONEditor(QMainWindow):
    def __init__(self, file_path=None):
        super().__init__()
        self.file_path = file_path
        self.current_json_data = None

        self.undo_stack = []
        logger.info(f"JSONEditor 初始化，文件路径: {file_path}")
        self.initUI()
        if self.file_path:
            self.load_json(self.file_path)

    def initUI(self):
        self.setWindowTitle('JSON 编辑器')
        self.setGeometry(200, 100, 1000, 700)

        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)

        control_layout = QHBoxLayout()

        self.load_btn = QPushButton('加载')
        # 只有当文件路径存在时才连接加载按钮的信号
        if self.file_path:
            self.load_btn.clicked.connect(lambda: self.load_json(self.file_path))
            logger.info(f"加载按钮已连接到文件: {self.file_path}")
        else:
            # 如果没有文件路径，可以禁用按钮或提供其他提示
            self.load_btn.setEnabled(False)
            logger.warning("未提供文件路径，加载按钮已禁用")
        control_layout.addWidget(self.load_btn)

        self.save_btn = QPushButton('保存')
        self.save_btn.clicked.connect(self.save_json)
        logger.info("保存按钮已连接")
        control_layout.addWidget(self.save_btn)

        self.undo_btn = QPushButton('撤销')
        self.undo_btn.clicked.connect(self.undo_edit)
        logger.info("撤销按钮已连接")
        control_layout.addWidget(self.undo_btn)

        layout.addLayout(control_layout)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(3)
        self.tree.setHeaderLabels(['键', '类型', '值'])
        self.tree.setEditTriggers(QAbstractItemView.NoEditTriggers) # 禁用双击编辑，我们用自定义对话框
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self.open_context_menu)
        layout.addWidget(self.tree)

        self.statusBar().showMessage('就绪')
        logger.info("UI 初始化完成")

    def open_context_menu(self, position):
        item = self.tree.itemAt(position)
        if not item:
            logger.debug("右键菜单：未点击到有效项")
            return

        logger.info(f"右键菜单：点击项 - 键: {item.text(0)}, 类型: {item.text(1)}")
        menu = QMenu()
        edit_action = QAction("编辑值", self)
        item_type = item.text(1)
        if item_type not in ["dict", "list"]:
            edit_action = QAction("编辑值", self)
            edit_action.triggered.connect(partial(self.open_edit_dialog, item))
            menu.addAction(edit_action)
            logger.debug("右键菜单：添加编辑值选项")
        
        if item_type == "list":
            add_action = QAction("添加元素", self)
            add_action.triggered.connect(partial(self.add_list_item, item))
            menu.addAction(add_action)
            logger.debug("右键菜单：添加添加元素选项")
            if item.parent(): # 只有非根列表项才能删除
                delete_action = QAction("删除元素", self)
                delete_action.triggered.connect(partial(self.delete_list_item, item))
                menu.addAction(delete_action)
                logger.debug("右键菜单：添加删除元素选项")
        
        menu.exec_(self.tree.viewport().mapToGlobal(position))

    def open_edit_dialog(self, item):
        old_value_str = item.text(2)
        item_type = item.text(1)
        logger.info(f"打开编辑对话框：键: {item.text(0)}, 类型: {item_type}, 旧值: {old_value_str}")

        self.edit_dialog = QWidget()
        self.edit_dialog.setWindowTitle("编辑值")
        self.edit_dialog.setMinimumSize(400, 150)
        layout = QVBoxLayout(self.edit_dialog)

        editor_widget = None
        if item_type == "bool":
            from PyQt5.QtWidgets import QComboBox
            editor_widget = QComboBox()
            editor_widget.addItem("True")
            editor_widget.addItem("False")
            if old_value_str == "True":
                editor_widget.setCurrentIndex(0)
            else:
                editor_widget.setCurrentIndex(1)
            logger.debug("编辑对话框：布尔类型编辑器")
        elif item_type in ["int", "float"]:
            from PyQt5.QtWidgets import QLineEdit, QDoubleValidator, QIntValidator
            editor_widget = QLineEdit()
            editor_widget.setText(old_value_str)
            if item_type == "int":
                editor_widget.setValidator(QIntValidator())
                logger.debug("编辑对话框：整数类型编辑器")
            else:
                editor_widget.setValidator(QDoubleValidator())
                logger.debug("编辑对话框：浮点数类型编辑器")
        else: # string, null, etc.
            editor_widget = QTextEdit()
            editor_widget.setPlainText(old_value_str)
            logger.debug("编辑对话框：文本类型编辑器")

        if editor_widget:
            layout.addWidget(editor_widget)

        btn = QPushButton("确定")
        btn.clicked.connect(partial(self.apply_edit, item, editor_widget, item_type, self.edit_dialog))
        layout.addWidget(btn)

        self.edit_dialog.show()

    def apply_edit(self, item, editor_widget, item_type, dialog):
        new_value = None
        if item_type == "bool":
            new_value = editor_widget.currentText()
        elif item_type in ["int", "float"]:
            new_value = editor_widget.text()
        else:
            new_value = editor_widget.toPlainText()

        logger.info(f"应用编辑：键: {item.text(0)}, 类型: {item_type}, 新值(原始): {new_value}")

        # 类型转换和验证
        try:
            if item_type == "int":
                new_value = str(int(new_value))
            elif item_type == "float":
                new_value = str(float(new_value))
            elif item_type == "bool":
                new_value = str(new_value == "True") # 确保存储为"True"或"False"
            elif item_type == "NoneType":
                new_value = "null" # 统一表示null
            # 对于字符串，直接使用new_value
            logger.debug(f"值类型转换成功，新值: {new_value}")
        except ValueError:
            QMessageBox.warning(self, "输入错误", f"无法将 '{new_value}' 转换为 {item_type} 类型")
            logger.error(f"输入错误: 无法将 '{new_value}' 转换为 {item_type} 类型")
            return

        self.undo_stack.append((item, item.text(2)))
        item.setText(2, new_value)
        dialog.close()
        self.update_json_data_from_tree() # 更新内部JSON数据结构
        logger.info(f"值已更新，键: {item.text(0)}, 新值: {new_value}")

    def undo_edit(self):
        if self.undo_stack:
            action = self.undo_stack.pop()
            if isinstance(action, tuple) and len(action) == 2: # 普通编辑的撤销
                item, prev_value = action
                item.setText(2, prev_value)
                logger.info(f"撤销普通编辑：键: {item.text(0)}, 恢复值: {prev_value}")
            elif isinstance(action, tuple) and action[0] == "delete": # 删除操作的撤销
                _, parent_item, item_index, item_data = action
                logger.info(f"撤销删除操作：父项: {parent_item.text(0)}, 索引: {item_index}")
                # 重新创建被删除的项
                # 注意：这里需要根据item_data的实际类型来创建QTreeWidgetItem，并递归添加子项
                # 假设item_data是一个字典，包含键、类型和值
                # 如果item_data是原始数据类型，直接创建即可
                # 如果item_data是复杂类型（dict/list），需要递归构建
                
                # 为了简化，我们假设item_data是parse_item_to_json返回的原始Python对象
                # 我们需要一个方法来从Python对象构建QTreeWidgetItem
                new_item = QTreeWidgetItem([f"[{item_index}]", self.get_type(item_data), '' if isinstance(item_data, (dict, list)) else str(item_data)])
                parent_item.insertChild(item_index, new_item)
                self.add_items(new_item, item_data) # 递归添加子项
                logger.debug(f"已恢复被删除项: {new_item.text(0)}")
                
                # 重新编号后续的列表项
                for i in range(item_index + 1, parent_item.childCount()):
                    child = parent_item.child(i)
                    child.setText(0, f"[{i}]")
                    child.setData(0, Qt.UserRole, i)
                logger.debug("已重新编号后续列表项")
            
            self.update_json_data_from_tree() # 撤销后更新内部JSON数据结构
            logger.info("撤销操作完成，已更新内部JSON数据")
        else:
            logger.warning("撤销栈为空，无法执行撤销操作")

    def load_json(self, file_path):
        logger.info(f"尝试加载JSON文件: {file_path}")
        if not os.path.isfile(file_path):
            QMessageBox.warning(self, "错误", "请选择有效的文件路径")
            logger.error(f"文件路径无效: {file_path}")
            return

        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            logger.success(f"JSON文件加载成功: {file_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"读取JSON失败: {e}")
            logger.error(f"读取JSON失败: {e}")
            return

        self.current_json_data = data
        self.file_path = file_path
        self.populate_tree(data)

    def populate_tree(self, data):
        logger.info("开始填充树形结构")
        self.tree.clear()
        root = QTreeWidgetItem(['根', self.get_type(data), ''])
        self.tree.addTopLevelItem(root)
        self.add_items(root, data)
        root.setExpanded(True)
        self.update_json_data_from_tree() # 加载后更新内部JSON数据结构
        logger.info("树形结构填充完成")

    def add_items(self, parent, value):
        if isinstance(value, dict):
            for k, v in value.items():
                value_display = '' if isinstance(v, (dict, list)) else str(v)
                child = QTreeWidgetItem([str(k), self.get_type(v), value_display])
                parent.addChild(child)
                self.add_items(child, v)
            logger.debug(f"添加字典项到父节点: {parent.text(0)}")
        elif isinstance(value, list):
            for idx, v in enumerate(value):
                value_display = '' if isinstance(v, (dict, list)) else str(v)
                child = QTreeWidgetItem([f"[{idx}]", self.get_type(v), value_display])
                child.setData(0, Qt.UserRole, idx) # 存储索引以便后续操作
                parent.addChild(child)
                self.add_items(child, v)
            logger.debug(f"添加列表项到父节点: {parent.text(0)}")

    def get_type(self, v):
        if isinstance(v, dict): return "dict"
        if isinstance(v, list): return "list"
        return type(v).__name__

    def tree_to_json(self):
        logger.info("开始将树形结构转换为JSON数据")
        def parse_item(item):
            child_count = item.childCount()
            key = item.text(0)
            value_text = item.text(2)
            if child_count == 0:
                # 尝试根据类型转换值
                if item.text(1) == "int":
                    return int(value_text)
                elif item.text(1) == "float":
                    return float(value_text)
                elif item.text(1) == "bool":
                    return value_text == "True"
                elif item.text(1) == "NoneType":
                    return None
                else:
                    return value_text # 默认作为字符串处理
            elif all(item.child(i).text(0).startswith('[') for i in range(child_count)):
                return [parse_item(item.child(i)) for i in range(child_count)]
            else:
                return {item.child(i).text(0): parse_item(item.child(i)) for i in range(child_count)}

        root = self.tree.topLevelItem(0)
        # 根节点本身不代表实际数据，它的子节点才是
        if root.childCount() == 1:
            # 如果根节点只有一个子节点，通常是加载的JSON的顶层是dict或list
            result = self.parse_item_to_json(root.child(0))
            logger.debug("树形结构转换为JSON成功 (单根节点)")
            return result
        # 如果根节点有多个子节点，或者没有子节点，说明JSON结构不是单个根对象/数组
        # 这通常发生在JSON文件本身是多个顶级元素，或者为空
        # 在这种情况下，我们应该返回一个与self.current_json_data结构一致的空字典或空列表
        # 根据实际情况，这里可能需要更复杂的逻辑来处理非标准根结构
        # 目前，我们假设根节点只有一个子节点代表整个JSON内容
        # 如果没有子节点，或者有多个，则返回一个空字典，这可能需要根据实际需求调整
        logger.warning("树形结构转换为JSON：根节点结构异常，返回空字典")
        return {} # 否则返回空字典或根据实际情况处理

    def parse_item_to_json(self, item):
        # 修正：key在这里可能不是实际的键，对于列表项，它是"[index]"形式
        # 我们主要依赖item_type和childCount来判断结构
        # key = item.text(0) # 这个变量在这里可能误导，因为列表项的key是索引字符串
        item_type = item.text(1)
        value_text = item.text(2)

        if item_type == "dict":
            result = {}
            for i in range(item.childCount()):
                child_item = item.child(i)
                child_key = child_item.text(0) # 字典的键是text(0)
                result[child_key] = self.parse_item_to_json(child_item)
            logger.debug(f"解析字典项: {item.text(0)}")
            return result
        elif item_type == "list":
            result = []
            for i in range(item.childCount()):
                child_item = item.child(i)
                result.append(self.parse_item_to_json(child_item))
            logger.debug(f"解析列表项: {item.text(0)}")
            return result
        else: # 叶子节点
            try:
                if item_type == "int":
                    return int(value_text)
                elif item_type == "float":
                    return float(value_text)
                elif item_type == "bool":
                    return value_text == "True"
                elif item_type == "NoneType":
                    return None
                else:
                    return value_text # 默认作为字符串处理
            except ValueError:
                logger.warning(f"解析叶子节点失败：无法将 '{value_text}' 转换为 {item_type} 类型，返回原始字符串")
                return value_text # 转换失败则返回原始字符串

    def update_json_data_from_tree(self):
        # 从树结构重新构建内部JSON数据
        self.current_json_data = self.parse_item_to_json(self.tree.topLevelItem(0))
        logger.info("内部JSON数据已从树形结构更新")

    def save_json(self):
        logger.info(f"尝试保存JSON文件: {self.file_path}")
        if not self.file_path:
            QMessageBox.warning(self, "错误", "没有文件可以保存")
            logger.error("没有文件路径可供保存")
            return
        try:
            with open(self.file_path, 'w', encoding='utf-8') as f:
                json.dump(self.tree_to_json(), f, indent=2, ensure_ascii=False)
            QMessageBox.information(self, "成功", f"文件已保存: {self.file_path}")
            logger.success(f"文件已保存: {self.file_path}")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"保存失败: {e}")
            logger.error(f"保存失败: {e}")

    def add_list_item(self, parent_item):
        logger.info(f"尝试向列表添加元素，父项: {parent_item.text(0)}")
        # 确保是列表类型
        if parent_item.text(1) != "list":
            logger.warning(f"尝试向非列表类型添加元素: {parent_item.text(1)}")
            return

        # 确定新元素的索引
        new_index = parent_item.childCount()
        new_item_text = f"[{new_index}]"

        # 添加一个默认的字符串类型元素
        new_child = QTreeWidgetItem([new_item_text, "str", "新元素"])
        new_child.setData(0, Qt.UserRole, new_index)
        parent_item.addChild(new_child)
        parent_item.setExpanded(True) # 展开父节点以便看到新添加的元素
        logger.info(f"已添加新元素: {new_item_text} 到列表")

        self.update_json_data_from_tree()

    def delete_list_item(self, item_to_delete):
        logger.info(f"尝试删除列表元素: {item_to_delete.text(0)}")
        parent_item = item_to_delete.parent()
        if not parent_item or parent_item.text(1) != "list":
            logger.warning(f"尝试删除非列表项或根列表项: {item_to_delete.text(0)}")
            return

        # 记录撤销信息
        item_index = item_to_delete.data(0, Qt.UserRole) # 获取原始索引
        # 递归地从QTreeWidgetItem构建Python对象，以便完整保存数据
        item_data_to_save = self.parse_item_to_json(item_to_delete)
        self.undo_stack.append(("delete", parent_item, item_index, item_data_to_save))
        logger.debug(f"删除操作已记录到撤销栈，索引: {item_index}, 数据: {item_data_to_save}")

        # 从树中移除
        parent_item.removeChild(item_to_delete)
        logger.info(f"已从树中移除元素: {item_to_delete.text(0)}")

        # 重新编号列表项
        for i in range(parent_item.childCount()):
            child = parent_item.child(i)
            child.setText(0, f"[{i}]")
            child.setData(0, Qt.UserRole, i) # 更新UserRole中的索引
        logger.debug("已重新编号列表项")

        self.update_json_data_from_tree()
        logger.info("删除操作完成，已更新内部JSON数据")

def edit_json(file_path):
    logger.info(f"启动JSON编辑器，文件路径: {file_path}")
    app = QApplication(sys.argv)
    editor = JSONEditor(file_path)
    editor.show()
    sys.exit(app.exec_())